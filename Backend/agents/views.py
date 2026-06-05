"""
Views for agents app.
"""

import json
import logging
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Agent, AgentTool, AgentConversation, AgentExecution
from .serializers import (
    AgentSerializer, AgentListSerializer, AgentToolSerializer,
    AgentConversationSerializer, AgentExecutionSerializer
)
from .engine import create_agent_engine, AgentEngine

logger = logging.getLogger(__name__)

DEBUG_HISTORY_LIMIT = 50


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
        return Agent.objects.filter(owner=self.request.user).select_related('tenant', 'owner')

    def get_serializer_class(self):
        if self.action == 'list':
            return AgentListSerializer
        return AgentSerializer

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

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
    def chat(self, request, pk=None):
        """Chat with the agent."""
        agent = self.get_object()
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
        conversation.save()

        engine = create_agent_engine(agent)
        result = engine.chat(message)

        if result.get('success'):
            response_content = result.get('response', '')
            conversation.messages.append({
                'role': 'assistant',
                'content': response_content
            })
            conversation.message_count += 1
            conversation.save()

            return Response({
                'conversation_id': conversation.id,
                'response': response_content,
                'tool_calls': result.get('tool_calls')
            })

        return Response({
            'error': result.get('error', 'Chat failed'),
            'conversation_id': conversation.id
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def stream_chat(self, request, pk=None):
        """Stream chat with the agent."""
        agent = self.get_object()
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
        conversation.save()

        engine = create_agent_engine(agent)

        def generate():
            full_response = ""
            try:
                for chunk in engine.stream_chat(message):
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
                        conversation.save()
                        yield f"data: {json.dumps({'type': 'done', 'conversation_id': str(conversation.id)})}\n\n"
                    elif chunk_type == 'error':
                        error_msg = chunk.get('error', 'Unknown error')
                        yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
            except Exception as e:
                logger.error(f"Stream chat error: {e}")
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
        message = request.data.get('message', '')
        context = request.data.get('context', {})

        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        engine = create_agent_engine(agent)
        result = engine.chat(message)

        is_success = result.get('success', False)
        execution_status = 'completed' if is_success else 'failed'

        execution = AgentExecution.objects.create(
            agent=agent,
            status=execution_status,
            input_data={'message': message, 'context': context},
            output_data={'response': result.get('response', '')},
            error_message=result.get('error', '') if not is_success else '',
            started_at=timezone.now(),
            completed_at=timezone.now()
        )

        if is_success:
            return Response({
                'response': result.get('response', ''),
                'tool_calls': result.get('tool_calls'),
                'execution_id': execution.id
            })

        return Response({
            'error': result.get('error', 'Debug failed'),
            'execution_id': execution.id
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

        if tool_name in agent.tools:
            agent.tools.remove(tool_name)
            agent.save()

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
                'id': execution.id,
                'conversation_id': execution.conversation_id,
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
        queryset = AgentConversation.objects.filter(
            agent__owner=self.request.user
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
        conversation.save()
        return Response({
            'messages': conversation.messages
        })


class AgentToolViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for available AgentTools."""

    serializer_class = AgentToolSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AgentTool.objects.filter(
            agent__owner=self.request.user
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
        return AgentExecution.objects.filter(
            agent__owner=self.request.user
        ).select_related('agent').order_by('-started_at')
