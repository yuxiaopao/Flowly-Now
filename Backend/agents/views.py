"""
Views for agents app.
"""

import asyncio
import json
import logging
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Agent, AgentTool, AgentConversation, AgentExecution, AgentCollaborationRun
from .serializers import (
    AgentSerializer, AgentListSerializer, AgentToolSerializer,
    AgentConversationSerializer, AgentExecutionSerializer,
    AgentCollaborationRunSerializer, AgentCollaborationRunListSerializer,
    AgentCollaborationRunCreateSerializer, AgentMarketplaceSerializer
)
from .engine import create_agent_engine, AgentEngine
from .multi_agent import create_multi_agent_chain

from tenants.access import get_accessible_tenant_ids, is_tenant_member, is_tenant_admin
from tenants.models import Tenant
from config.constants import DEFAULT_LLM_MODEL, DEFAULT_TEMPERATURE

logger = logging.getLogger(__name__)

DEBUG_HISTORY_LIMIT = 50
TOKEN_ESTIMATE_RATIO = 4  # chars per token estimate (English-heavy text)
COLLABORATION_TIMEOUT_SECONDS = 300
COLLABORATION_ROLES = ('planner', 'executor', 'critic', 'reporter')
DEFAULT_ROLE_SYSTEM_PROMPTS = {
    'planner': '你是一名任务规划专家，负责将复杂任务拆解为清晰的可执行步骤。',
    'executor': '你是一名任务执行专家，负责按照计划完成具体工作并给出结果。',
    'critic': '你是一名质量审核专家，负责审查执行结果是否满足任务要求，并提出改进建议。',
    'reporter': '你是一名报告撰写专家，负责将各阶段结果整理成清晰、结构化的最终报告。',
}
ROLE_DISPLAY_NAMES = {
    'planner': 'Planner（规划者）',
    'executor': 'Executor（执行者）',
    'critic': 'Critic（审查者）',
    'reporter': 'Reporter（报告者）',
}


def _estimate_tokens(text: str) -> int:
    """Estimate token count from text using a simple char-based heuristic.

    This is an approximation suitable for tracking relative token usage.
    For accurate billing, replace with tiktoken or similar library.
    """
    return max(1, len(text) // TOKEN_ESTIMATE_RATIO)


def _validate_knowledge_collections(user, collection_ids):
    """Ensure the user may bind each given DocumentCollection id to an agent
    (must own it, or it must be shared with a tenant the user belongs to)."""
    if not collection_ids:
        return
    from rag.models import DocumentCollection

    tenant_ids = get_accessible_tenant_ids(user)
    accessible_ids = set(str(cid) for cid in DocumentCollection.objects.filter(
        Q(owner=user) | Q(tenant_id__in=tenant_ids)
    ).values_list('id', flat=True))

    invalid_ids = [str(cid) for cid in collection_ids if str(cid) not in accessible_ids]
    if invalid_ids:
        raise ValidationError({
            'knowledge_collections': f'您无权关联以下知识库集合: {", ".join(invalid_ids)}'
        })


def _stringify_trace_value(value):
    """Render a trace step's content as human-readable text (JSON for dict/list)."""
    if isinstance(value, str):
        return value
    if value is None:
        return ''
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value)


def _build_collaboration_trace(result, roles_config_snapshot):
    """Turn a MultiAgentOrchestrator TaskResult into an ordered list of trace steps."""
    trace = []
    output = result.output if isinstance(result.output, dict) else {}
    role_names = {r['role']: r['name'] for r in roles_config_snapshot}
    now_iso = timezone.now().isoformat()

    if 'plan' in output:
        trace.append({
            'phase': 'planning',
            'role': 'planner',
            'agent': role_names.get('planner', ROLE_DISPLAY_NAMES['planner']),
            'content': _stringify_trace_value(output['plan']),
            'timestamp': now_iso,
        })
    if 'execution' in output:
        execution = output['execution']
        exec_content = getattr(execution, 'output', execution)
        trace.append({
            'phase': 'execution',
            'role': 'executor',
            'agent': role_names.get('executor', ROLE_DISPLAY_NAMES['executor']),
            'content': _stringify_trace_value(exec_content),
            'timestamp': now_iso,
        })
    if 'review' in output:
        trace.append({
            'phase': 'review',
            'role': 'critic',
            'agent': role_names.get('critic', ROLE_DISPLAY_NAMES['critic']),
            'content': _stringify_trace_value(output['review']),
            'timestamp': now_iso,
        })
    if 'report' in output:
        trace.append({
            'phase': 'report',
            'role': 'reporter',
            'agent': role_names.get('reporter', ROLE_DISPLAY_NAMES['reporter']),
            'content': _stringify_trace_value(output['report']),
            'timestamp': now_iso,
        })
    if not trace and result.error:
        trace.append({
            'phase': 'error',
            'role': 'system',
            'agent': 'system',
            'content': result.error,
            'timestamp': now_iso,
        })
    return trace


def _extract_final_report(result):
    """Pick the best available textual output from a completed collaboration run."""
    output = result.output if isinstance(result.output, dict) else {}

    if 'report' in output:
        report_text = _stringify_trace_value(output['report'])
        if report_text and report_text.strip():
            return report_text

    if 'review' in output:
        review_text = _stringify_trace_value(output['review'])
        if review_text and review_text.strip():
            return review_text

    if 'execution' in output:
        execution = output['execution']
        exec_text = _stringify_trace_value(getattr(execution, 'output', execution))
        if exec_text and exec_text.strip():
            return exec_text

    if 'plan' in output:
        plan_text = _stringify_trace_value(output['plan'])
        if plan_text and plan_text.strip():
            return plan_text

    fallback = _stringify_trace_value(result.output)
    return fallback if fallback and fallback.strip() else ''


def _get_or_create_conversation(agent, user, conversation_id=None):
    """Get existing conversation or create new one. Returns tuple (conversation, created)."""
    if conversation_id:
        try:
            conversation = AgentConversation.objects.get(
                id=conversation_id,
                agent=agent,
                user=user
            )
            return conversation, False
        except AgentConversation.DoesNotExist:
            pass

    conversation = AgentConversation.objects.create(
        agent=agent,
        user=user,
        messages=[]
    )
    return conversation, True


class AgentViewSet(viewsets.ModelViewSet):
    """ViewSet for Agent model."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant_ids = get_accessible_tenant_ids(self.request.user)
        queryset = Agent.objects.filter(
            Q(owner=self.request.user) | Q(tenant_id__in=tenant_ids)
        ).distinct().select_related('tenant', 'owner')
        tenant_param = self.request.query_params.get('tenant')
        if tenant_param:
            queryset = queryset.filter(tenant_id=tenant_param)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return AgentListSerializer
        return AgentSerializer

    def perform_create(self, serializer):
        tenant = serializer.validated_data.get('tenant')
        if tenant is not None and not is_tenant_member(self.request.user, tenant.id):
            raise ValidationError({'tenant': '您不是该团队的成员，无法将 Agent 共享到此团队。'})
        _validate_knowledge_collections(self.request.user, serializer.validated_data.get('knowledge_collections'))
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        user = self.request.user
        if instance.owner_id != user.id and not user.is_superuser:
            if not (instance.tenant_id and is_tenant_admin(user, instance.tenant_id)):
                raise ValidationError({'detail': '仅所有者或团队管理员可编辑该 Agent。'})
        tenant = serializer.validated_data.get('tenant')
        if tenant is not None and not is_tenant_member(user, tenant.id):
            raise ValidationError({'tenant': '您不是该团队的成员，无法将 Agent 共享到此团队。'})
        _validate_knowledge_collections(user, serializer.validated_data.get('knowledge_collections'))
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.owner_id != user.id and not user.is_superuser:
            if not (instance.tenant_id and is_tenant_admin(user, instance.tenant_id)):
                raise ValidationError({'detail': '仅所有者或团队管理员可删除该 Agent。'})
        instance.delete()

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate an agent."""
        source = self.get_object()
        serializer = self.get_serializer(source)
        data = dict(serializer.data)
        for key in ['id', 'created_at', 'updated_at']:
            data.pop(key, None)
        data['name'] = f"{source.name} (副本)"
        data['is_active'] = True
        new_serializer = self.get_serializer(data=data)
        new_serializer.is_valid(raise_exception=True)
        new_serializer.save(owner=request.user)
        return Response(new_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish an agent to the public marketplace (owner-only)."""
        agent = self.get_object()
        if agent.owner_id != request.user.id and not request.user.is_superuser:
            return Response({'error': '仅所有者可发布该 Agent 到市场。'}, status=status.HTTP_403_FORBIDDEN)
        agent.is_public = True
        agent.save(update_fields=['is_public', 'updated_at'])
        return Response(self.get_serializer(agent).data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Remove an agent from the public marketplace (owner-only)."""
        agent = self.get_object()
        if agent.owner_id != request.user.id and not request.user.is_superuser:
            return Response({'error': '仅所有者可从市场下架该 Agent。'}, status=status.HTTP_403_FORBIDDEN)
        agent.is_public = False
        agent.save(update_fields=['is_public', 'updated_at'])
        return Response(self.get_serializer(agent).data)

    @action(detail=False, methods=['get'])
    def marketplace(self, request):
        """Browse all publicly published agents across the platform (desensitized)."""
        queryset = Agent.objects.filter(is_public=True, is_active=True).select_related('owner', 'tenant').order_by('-updated_at')

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        agent_type = request.query_params.get('agent_type')
        if agent_type:
            queryset = queryset.filter(agent_type=agent_type)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AgentMarketplaceSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AgentMarketplaceSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone a publicly published agent (from the marketplace) into the caller's own agents.

        Unlike `duplicate`, this bypasses the owner/tenant-scoped queryset since the
        source agent may belong to another user; it is only accessible here because
        it is marked `is_public=True`. The clone starts with no tenant sharing and no
        knowledge base bindings, since the cloner may not have access to the original
        owner's team or document collections.
        """
        try:
            source = Agent.objects.get(pk=pk, is_public=True, is_active=True)
        except Agent.DoesNotExist:
            return Response({'error': '该 Agent 不存在或未发布到市场。'}, status=status.HTTP_404_NOT_FOUND)

        new_agent = Agent.objects.create(
            owner=request.user,
            tenant=None,
            name=f"{source.name} (克隆)",
            description=source.description,
            agent_type=source.agent_type,
            system_prompt=source.system_prompt,
            model=source.model,
            temperature=source.temperature,
            max_tokens=source.max_tokens,
            tools=source.tools,
            skills=source.skills,
            memory_enabled=source.memory_enabled,
            context_window=source.context_window,
            knowledge_collections=[],
            is_public=False,
            is_active=True,
        )
        return Response(self.get_serializer(new_agent).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def chat(self, request, pk=None):
        """Chat with the agent."""
        agent = self.get_object()
        if not agent.is_active:
            return Response(
                {'error': 'Agent is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        message = request.data.get('message', '')
        conversation_id = request.data.get('conversation_id')

        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conversation, _ = _get_or_create_conversation(agent, request.user, conversation_id)

        conversation.messages.append({
            'role': 'user',
            'content': message
        })
        conversation.message_count += 1
        conversation.token_count += _estimate_tokens(message)
        conversation.save()

        engine = create_agent_engine(agent, conversation)
        result = engine.chat(message)

        if result.get('success'):
            response_content = result.get('response', '')
            conversation.messages.append({
                'role': 'assistant',
                'content': response_content
            })
            conversation.message_count += 1
            conversation.token_count += _estimate_tokens(response_content)
            conversation.save()

            return Response({
                'conversation_id': str(conversation.id),
                'response': response_content,
                'tool_calls': result.get('tool_calls')
            })

        return Response({
            'error': result.get('error', 'Chat failed'),
            'conversation_id': str(conversation.id)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def stream_chat(self, request, pk=None):
        """Stream chat with the agent."""
        agent = self.get_object()
        if not agent.is_active:
            return Response(
                {'error': 'Agent is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        message = request.data.get('message', '')
        conversation_id = request.data.get('conversation_id')

        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conversation, _ = _get_or_create_conversation(agent, request.user, conversation_id)

        conversation.messages.append({
            'role': 'user',
            'content': message
        })
        conversation.message_count += 1
        conversation.token_count += _estimate_tokens(message)
        conversation.save()

        engine = create_agent_engine(agent, conversation)
        # Track whether streaming completed so we can compensate on failure
        stream_ok = False

        def generate():
            nonlocal stream_ok
            full_response = ""
            chunk_count = 0
            try:
                for chunk in engine.stream_chat(message):
                    chunk_count += 1
                    # Send a ping comment every 10 chunks to prevent Chrome SSE timeout.
                    # Chrome drops SSE connections after ~30s of inactivity.
                    if chunk_count % 10 == 0:
                        yield f": ping\n\n"
                    chunk_type = chunk.get('type')
                    if chunk_type == 'content':
                        content = chunk.get('content', '')
                        full_response += content
                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                    elif chunk_type == 'done':
                        conversation.messages.append({
                            'role': 'assistant',
                            'content': full_response
                        })
                        conversation.message_count += 1
                        conversation.token_count += _estimate_tokens(full_response)
                        conversation.save()
                        stream_ok = True
                        yield f"data: {json.dumps({'type': 'done', 'conversation_id': str(conversation.id), 'tool_calls': chunk.get('tool_calls')})}\n\n"
                    elif chunk_type == 'error':
                        error_msg = chunk.get('error', 'Unknown error')
                        yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
            except Exception as e:
                logger.error(f"Stream chat error: {e}")
                # Compensate: remove the orphaned user message
                if not stream_ok:
                    try:
                        conversation.messages.pop()
                        conversation.message_count = max(0, conversation.message_count - 1)
                        conversation.save(update_fields=['messages', 'message_count'])
                    except Exception as rollback_err:
                        logger.error(f"Rollback failed: {rollback_err}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        response = StreamingHttpResponse(
            generate(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    @action(detail=True, methods=['post'])
    def debug(self, request, pk=None):
        """Debug agent with a message."""
        agent = self.get_object()
        if not agent.is_active:
            return Response(
                {'error': 'Agent is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        message = request.data.get('message', '')
        context = request.data.get('context', {})

        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        engine = create_agent_engine(agent)
        execution = AgentExecution.objects.create(
            agent=agent,
            status='running',
            input_data={'message': message, 'context': context},
        )

        try:
            result = engine.chat(message)
        except Exception as e:
            logger.error(f"debug() engine.chat() failed: {e}")
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()
            return Response({
                'error': str(e),
                'execution_id': str(execution.id)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        is_success = isinstance(result, dict) and result.get('success', False)
        try:
            execution.output_data = {'response': result.get('response', '')} if isinstance(result, dict) else {}
            execution.error_message = result.get('error', '') if (isinstance(result, dict) and not is_success) else ''
            execution.status = 'completed' if is_success else 'failed'
            execution.completed_at = timezone.now()
            execution.save()
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()

        if is_success:
            return Response({
                'response': result.get('response', ''),
                'tool_calls': result.get('tool_calls'),
                'execution_id': str(execution.id)
            })

        return Response({
            'error': result.get('error', 'Debug failed'),
            'execution_id': str(execution.id)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get', 'delete'])
    def debug_history(self, request, pk=None):
        """Get or clear debug history for an agent."""
        agent = self.get_object()

        if request.method == 'DELETE':
            # Only delete executions for agents owned by the requesting user
            AgentExecution.objects.filter(
                agent=agent,
                agent__owner=request.user
            ).delete()
            return Response({'message': 'Debug history cleared'})

        executions = AgentExecution.objects.filter(
            agent=agent,
            agent__owner=request.user
        ).order_by('-started_at')

        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = AgentExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AgentExecutionSerializer(executions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def tools(self, request, pk=None):
        """Get or add tools for an agent."""
        agent = self.get_object()

        if request.method == 'GET':
            available_tools = AgentEngine.TOOLS_REGISTRY.keys()
            return Response({
                'available_tools': list(available_tools),
                'agent_tools': agent.tools
            })

        elif request.method == 'POST':
            tool_names = request.data.get('tools', [])
            agent.tools = tool_names
            agent.save()
            return Response({
                'tools': agent.tools
            })

    @action(detail=True, methods=['delete'])
    def tools_remove(self, request, pk=None):
        """Remove a tool from agent."""
        agent = self.get_object()
        tool_name = request.data.get('tool')

        if tool_name and isinstance(agent.tools, list) and tool_name in agent.tools:
            agent.tools.remove(tool_name)
            agent.save(update_fields=['tools'])

        return Response({
            'tools': agent.tools
        })

    @action(detail=True, methods=['post'])
    def reset_memory(self, request, pk=None):
        """Reset agent conversation memory."""
        agent = self.get_object()
        engine = create_agent_engine(agent)
        engine.reset_memory()
        return Response({'message': 'Memory reset successfully'})

    @action(detail=True, methods=['get'])
    def skills(self, request, pk=None):
        """Get agent skills."""
        agent = self.get_object()
        return Response({
            'skills': agent.skills
        })

    @action(detail=True, methods=['patch'])
    def update_skills(self, request, pk=None):
        """Update agent skills."""
        agent = self.get_object()
        skills = request.data.get('skills', [])
        agent.skills = skills
        agent.save()
        return Response({
            'skills': agent.skills
        })

    @action(detail=True, methods=['get'], url_path='debug/sessions/(?P<session_id>[^/.]+)')
    def debug_session_detail(self, request, pk=None, session_id=None):
        """Load a specific debug session with its messages."""
        agent = self.get_object()

        try:
            execution = AgentExecution.objects.select_related('agent').get(
                id=session_id,
                agent=agent,
                agent__owner=request.user
            )

            messages = []
            if execution.input_data and isinstance(execution.input_data, dict):
                if 'message' in execution.input_data:
                    messages.append({
                        'role': 'user',
                        'content': execution.input_data['message']
                    })

            if execution.output_data and isinstance(execution.output_data, dict):
                if 'response' in execution.output_data:
                    messages.append({
                        'role': 'assistant',
                        'content': execution.output_data['response']
                    })

            return Response({
                'id': str(execution.id),
                'conversation_id': str(execution.conversation_id) if execution.conversation_id else None,
                'agent_id': agent.id,
                'status': execution.status,
                'started_at': execution.started_at,
                'completed_at': execution.completed_at,
                'messages': messages,
                'message_count': len(messages),
                'input_data': execution.input_data,
                'output_data': execution.output_data,
                'error': execution.error_message
            })
        except AgentExecution.DoesNotExist:
            return Response(
                {'error': 'Session not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class AgentConversationViewSet(viewsets.ModelViewSet):
    """ViewSet for AgentConversation model."""

    serializer_class = AgentConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        queryset = AgentConversation.objects.filter(
            Q(agent__owner=user) | Q(agent__tenant_id__in=tenant_ids)
        ).select_related('agent', 'user')
        agent_id = self.request.query_params.get('agent_id')
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
        return queryset.order_by('-updated_at')

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get messages for a conversation."""
        conversation = self.get_object()
        return Response({
            'messages': conversation.messages,
            'message_count': conversation.message_count,
            'token_count': conversation.token_count
        })

    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Add a message to conversation."""
        conversation = self.get_object()
        role = request.data.get('role')
        content = request.data.get('content')

        if not content:
            return Response(
                {'error': 'Content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if role not in ['user', 'assistant', 'system']:
            return Response(
                {'error': 'Invalid role'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conversation.messages.append({
            'role': role,
            'content': content
        })
        conversation.message_count += 1
        conversation.token_count += _estimate_tokens(content)
        conversation.save()
        return Response({
            'messages': conversation.messages
        })


class AgentToolViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for available AgentTools."""

    serializer_class = AgentToolSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        return AgentTool.objects.filter(
            Q(agent__owner=user) | Q(agent__tenant_id__in=tenant_ids)
        ).select_related('agent')

    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get list of available tool types."""
        available_tools = [
            {
                'name': name,
                'description': tool_class.__doc__ or '',
                'schema': tool_class.parameters if hasattr(tool_class, 'parameters') else {}
            }
            for name, tool_class in AgentEngine.TOOLS_REGISTRY.items()
        ]
        return Response(available_tools)


class AgentExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AgentExecution model."""

    serializer_class = AgentExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        return AgentExecution.objects.filter(
            Q(agent__owner=user) | Q(agent__tenant_id__in=tenant_ids)
        ).select_related('agent').order_by('-started_at')


class AgentCollaborationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """ViewSet for multi-agent collaboration runs: launch new runs + browse/delete history.

    Intentionally excludes create/update - collaboration runs are only ever created via
    the `run` action (which drives the orchestrator synchronously) and are immutable once
    recorded, so no generic PUT/PATCH is exposed.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        queryset = AgentCollaborationRun.objects.filter(
            Q(created_by=user) | Q(tenant_id__in=tenant_ids)
        ).distinct().select_related('tenant', 'created_by')
        tenant_param = self.request.query_params.get('tenant')
        if tenant_param:
            queryset = queryset.filter(tenant_id=tenant_param)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return AgentCollaborationRunListSerializer
        return AgentCollaborationRunSerializer

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.created_by_id != user.id and not user.is_superuser:
            if not (instance.tenant_id and is_tenant_admin(user, instance.tenant_id)):
                raise ValidationError({'detail': '仅发起人或团队管理员可删除该协作记录。'})
        instance.delete()

    def _resolve_role_config(self, role_item, user, accessible_tenant_ids):
        """Resolve a single role's engine config, optionally inheriting from a bound Agent."""
        role_name = role_item['role']
        agent_id = role_item.get('agent_id')
        bound_agent = None

        if agent_id:
            try:
                bound_agent = Agent.objects.get(id=agent_id)
            except Agent.DoesNotExist:
                raise ValueError(f'角色 {role_name} 绑定的 Agent 不存在')
            if bound_agent.owner_id != user.id and bound_agent.tenant_id not in accessible_tenant_ids:
                raise ValueError(f'您无权使用角色 {role_name} 绑定的 Agent')

        if bound_agent:
            engine_config = {
                'role': role_name,
                'system_prompt': bound_agent.system_prompt or DEFAULT_ROLE_SYSTEM_PROMPTS[role_name],
                'model': bound_agent.model or DEFAULT_LLM_MODEL,
                'tools': bound_agent.tools or [],
                'knowledge_collection_ids': bound_agent.knowledge_collections or [],
            }
            display_name = bound_agent.name
            model_used = bound_agent.model or DEFAULT_LLM_MODEL
        else:
            engine_config = {
                'role': role_name,
                'system_prompt': role_item.get('system_prompt') or DEFAULT_ROLE_SYSTEM_PROMPTS[role_name],
                'model': role_item.get('model') or DEFAULT_LLM_MODEL,
                'tools': [],
                'knowledge_collection_ids': [],
            }
            display_name = role_item.get('name') or ROLE_DISPLAY_NAMES[role_name]
            model_used = engine_config['model']

        snapshot = {
            'role': role_name,
            'agent_id': str(agent_id) if agent_id else None,
            'name': display_name,
            'model': model_used,
        }
        return engine_config, snapshot

    @action(detail=False, methods=['post'])
    def run(self, request):
        """Launch and synchronously execute a new multi-agent collaboration run."""
        request_serializer = AgentCollaborationRunCreateSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        task = request_serializer.validated_data['task']
        tenant_obj = request_serializer.validated_data.get('tenant')
        roles_input = request_serializer.validated_data.get('roles') or []

        if tenant_obj is not None:
            if not is_tenant_member(request.user, tenant_obj.id):
                return Response({'error': '您不是该团队的成员'}, status=status.HTTP_403_FORBIDDEN)

        if not roles_input:
            roles_input = [{'role': r} for r in COLLABORATION_ROLES]

        seen_roles = set()
        agents_config = {}
        roles_config_snapshot = []
        accessible_tenant_ids = get_accessible_tenant_ids(request.user)

        for role_item in roles_input:
            role_name = role_item['role']
            if role_name not in COLLABORATION_ROLES:
                return Response(
                    {'error': f'暂不支持角色 {role_name}，仅支持: {", ".join(COLLABORATION_ROLES)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if role_name in seen_roles:
                return Response({'error': f'角色 {role_name} 重复配置'}, status=status.HTTP_400_BAD_REQUEST)
            seen_roles.add(role_name)

            try:
                engine_config, snapshot = self._resolve_role_config(role_item, request.user, accessible_tenant_ids)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)

            agents_config[role_name] = engine_config
            roles_config_snapshot.append(snapshot)

        if 'planner' not in agents_config and 'executor' not in agents_config:
            return Response({'error': '至少需要配置 planner 或 executor 角色'}, status=status.HTTP_400_BAD_REQUEST)

        run = AgentCollaborationRun.objects.create(
            tenant=tenant_obj,
            created_by=request.user,
            task=task,
            roles_config=roles_config_snapshot,
            status='running',
        )

        try:
            orchestrator = create_multi_agent_chain(
                agents_config,
                llm_config={'model': DEFAULT_LLM_MODEL, 'temperature': DEFAULT_TEMPERATURE}
            )
            orchestrator.timeout_seconds = COLLABORATION_TIMEOUT_SECONDS
            result = asyncio.run(orchestrator.run(task))
        except Exception as e:
            logger.error(f"Collaboration run {run.id} failed: {e}")
            run.status = 'failed'
            run.error_message = str(e)
            run.completed_at = timezone.now()
            run.save()
            return Response({'error': str(e), 'run_id': str(run.id)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        run.trace = _build_collaboration_trace(result, roles_config_snapshot)
        if result.success:
            run.status = 'completed'
            run.final_report = _extract_final_report(result)
        else:
            run.status = 'failed'
            run.error_message = result.error or '协作任务执行失败'
        run.completed_at = timezone.now()
        run.save()

        serializer = AgentCollaborationRunSerializer(run)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
