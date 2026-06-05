"""
Views for NL to Workflow.
Unifies API response format across all endpoints.
"""

import json
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
try:
    from ratelimit.decorators import ratelimit
except ImportError:
    from django_ratelimit.decorators import ratelimit

from .models import NLSession
from .services import get_nl_service, NLToWorkflowService, analyze_intent
from workflows.models import Workflow, Node, Edge
from workflows.serializers import WorkflowDetailSerializer, NodeSerializer, EdgeSerializer
from config.constants import DEFAULT_MAX_TOKENS


# ---------------------------------------------------------------------------
# Constants - externalized from code for maintainability
# ---------------------------------------------------------------------------

DEFAULT_TEMPERATURE = 0.7

ERROR_SESSION_NOT_FOUND = '会话不存在'
ERROR_NO_WORKFLOW = '没有生成的工作流'
ERROR_NO_DESCRIPTION = '请提供工作流描述'
ERROR_NO_MESSAGE = '请提供消息内容'
ERROR_NO_PROVIDER = '没有可用的 LLM provider'

# Streaming configuration
STREAM_CHUNK_SIZE = 1024


def get_nl_service_for_request(request, model=None, temperature=DEFAULT_TEMPERATURE):
    """Create an NL service configured for the current request."""
    return get_nl_service(
        model=model,
        temperature=temperature,
        max_tokens=DEFAULT_MAX_TOKENS,
        user=request.user
    )


def _build_session_response(session, include_workflow=False):
    """Build a consistent session response dict."""
    data = {
        'session_id': session.id,
        'name': session.name,
        'description': session.description,
        'workflow_id': session.workflow_id,
        'workflow_json': session.workflow_json,
        'workflow_name': session.workflow_name,
        'status': session.status,
        'error_message': session.error_message or None,
        'messages': session.messages,
        'node_count': len(session.workflow_json.get('nodes', [])) if session.workflow_json else 0,
        'edge_count': len(session.workflow_json.get('edges', [])) if session.workflow_json else 0,
        'created_at': session.created_at,
        'updated_at': session.updated_at,
    }
    if include_workflow and session.workflow_json:
        data['workflow'] = session.workflow_json
    return data


def _build_session_list_item(session):
    """Build a session item for list responses (lighter than full response)."""
    return {
        'session_id': session.id,
        'name': session.name,
        'description': session.description,
        'workflow_id': session.workflow_id,
        'workflow_name': session.workflow_name,
        'status': session.status,
        'error_message': session.error_message or None,
        'node_count': len(session.workflow_json.get('nodes', [])) if session.workflow_json else 0,
        'created_at': session.created_at,
        'updated_at': session.updated_at,
    }


class NLModelListView(APIView):
    """List available models for NL-to-workflow generation."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return available models from the provider registry."""
        service = NLToWorkflowService(user=request.user)
        models = service.list_available_models()
        default_model = service._resolve_model() or (models[0]['model_id'] if models else None)
        return Response({
            'models': models,
            'default': default_model,
            'count': len(models)
        })


class NLSessionViewSet(APIView):
    """ViewSet for NL sessions - handles list and create."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's NL sessions."""
        sessions = NLSession.objects.filter(
            user=request.user
        ).order_by('-updated_at')[:20]
        return Response({
            'code': 0,
            'message': 'success',
            'data': [_build_session_list_item(s) for s in sessions],
            'count': len(sessions)
        })

    def post(self, request):
        """Create a new NL session and generate workflow."""
        description = request.data.get('description', '')
        name = request.data.get(
            'name',
            f'NL Workflow {NLSession.objects.filter(user=request.user).count() + 1}'
        )
        model = request.data.get('model')
        temperature = float(request.data.get('temperature', DEFAULT_TEMPERATURE))

        if not description:
            return Response(
                {'error': ERROR_NO_DESCRIPTION},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = NLSession.objects.create(
            user=request.user,
            name=name,
            description=description,
            messages=[]
        )

        import traceback as tb_module
        try:
            nl_service = get_nl_service_for_request(request, model=model, temperature=temperature)

            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"NL service created, model={model}")

            workflow_data = nl_service.generate_workflow(description)
            logger.info(f"Workflow generation result: {list(workflow_data.keys())}")

            if 'error' in workflow_data:
                session.status = 'failed'
                session.error_message = workflow_data['error']
                session.save()
                return Response({
                    'session_id': session.id,
                    'error': workflow_data['error'],
                    'status': 'failed'
                }, status=status.HTTP_400_BAD_REQUEST)

            session.workflow_json = workflow_data
            session.workflow_name = workflow_data.get('name', name)
            session.messages.append({
                'role': 'assistant',
                'content': f'已生成工作流: {session.workflow_name}'
            })
            session.save()

            return Response({
                'session_id': session.id,
                'workflow_json': workflow_data,
                'workflow': workflow_data,  # Alias for backward compatibility
                'workflow_name': session.workflow_name,
                'status': session.status,
                'message': '工作流生成成功'
            })

        except Exception as e:
            import traceback
            session.status = 'failed'
            session.error_message = str(e)
            session.save()
            import logging
            logging.getLogger(__name__).exception(f"NL workflow generation failed: {e}")
            return Response({
                'session_id': session.id,
                'error': str(e),
                'status': 'failed',
                'traceback': traceback.format_exc(),
            }, status=status.HTTP_400_BAD_REQUEST)


class NLSessionDetailView(APIView):
    """Detail view for NL session."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        """Get session details."""
        try:
            session = NLSession.objects.get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(_build_session_response(session, include_workflow=True))

    def delete(self, request, session_id):
        """Delete session."""
        try:
            session = NLSession.objects.get(id=session_id, user=request.user)
            session.delete()
            return Response({'message': '会话已删除'})
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, session_id):
        """Update session (rename, etc.)."""
        try:
            session = NLSession.objects.get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        name = request.data.get('name')
        if name is not None:
            session.name = name.strip()[:200]
            session.save(update_fields=['name', 'updated_at'])

        return Response({
            'session_id': session.id,
            'name': session.name,
            'message': '会话已更新'
        })


class NLSessionMessageView(APIView):
    """Handle conversation messages in NL session."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        """Send a message and continue conversation."""
        try:
            session = NLSession.objects.get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        user_message = request.data.get('message', '')
        model = request.data.get('model')
        temperature = float(request.data.get('temperature', DEFAULT_TEMPERATURE))

        if not user_message:
            return Response(
                {'error': ERROR_NO_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.messages.append({
            'role': 'user',
            'content': user_message
        })

        try:
            nl_service = get_nl_service_for_request(request, model=model, temperature=temperature)
            response = nl_service.continue_conversation(
                session.messages[:-1],
                user_message,
                current_workflow=session.workflow_json if session.workflow_json else None
            )

            session.messages.append({
                'role': 'assistant',
                'content': response.get('message', '')
            })

            # If workflow was modified, update session
            if response.get('workflow'):
                session.workflow_json = response['workflow']
                session.workflow_name = response['workflow'].get('name', session.workflow_name)

            session.save()

            return Response({
                'message': response.get('message', ''),
                'suggestions': response.get('suggestions', []),
                'workflow_json': response.get('workflow'),
                'workflow': response.get('workflow'),  # Alias for backward compatibility
                'changes': response.get('changes', [])
            })

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NLSessionMessageStreamView(APIView):
    """
    Stream message response for NL session.
    
    POST /api/v1/nl-workflow/sessions/<uuid:session_id>/message/stream/
    Body: { message, model?, temperature? }
    
    Returns StreamingHttpResponse with Server-Sent Events (SSE).
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def post(self, request, session_id):
        """Send a message and stream the response."""
        try:
            session = NLSession.objects.get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        user_message = request.data.get('message', '')
        model = request.data.get('model')
        temperature = float(request.data.get('temperature', DEFAULT_TEMPERATURE))

        if not user_message:
            return Response(
                {'error': ERROR_NO_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.messages.append({
            'role': 'user',
            'content': user_message
        })

        def generate_stream():
            """Generator for streaming response."""
            try:
                nl_service = get_nl_service_for_request(request, model=model, temperature=temperature)
                
                # Yield initial progress
                yield f"data: {json.dumps({'type': 'progress', 'stage': 'thinking', 'message': '正在理解您的需求...', 'progress': 10}, ensure_ascii=False)}\n\n"
                
                # Continue conversation
                response = nl_service.continue_conversation(
                    session.messages[:-1],
                    user_message,
                    current_workflow=session.workflow_json if session.workflow_json else None
                )
                
                # Yield workflow if updated
                if response.get('workflow'):
                    session.workflow_json = response['workflow']
                    session.workflow_name = response['workflow'].get('name', session.workflow_name)
                    session.save()
                    
                    yield f"data: {json.dumps({'type': 'workflow', 'workflow': response['workflow'], 'progress': 80}, ensure_ascii=False)}\n\n"
                
                # Save assistant message
                assistant_content = response.get('message', '')
                session.messages.append({
                    'role': 'assistant',
                    'content': assistant_content
                })
                session.save()
                
                # Yield suggestions
                suggestions = response.get('suggestions', [])
                if suggestions:
                    yield f"data: {json.dumps({'type': 'suggestions', 'suggestions': suggestions}, ensure_ascii=False)}\n\n"
                
                # Yield changes if any
                changes = response.get('changes', [])
                if changes:
                    yield f"data: {json.dumps({'type': 'changes', 'changes': changes}, ensure_ascii=False)}\n\n"
                
                # Yield final done message
                yield f"data: {json.dumps({'type': 'done', 'message': assistant_content, 'progress': 100}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                import logging
                logging.exception("Streaming message failed")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        response = StreamingHttpResponse(
            generate_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class NLSessionConfirmView(APIView):
    """Confirm and save generated workflow."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, session_id):
        """Save generated workflow to database."""
        try:
            session = NLSession.objects.get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        if not session.workflow_json:
            return Response(
                {'error': ERROR_NO_WORKFLOW},
                status=status.HTTP_400_BAD_REQUEST
            )

        workflow_data = session.workflow_json

        # Create workflow
        workflow = Workflow.objects.create(
            name=workflow_data.get('name', session.workflow_name),
            description=workflow_data.get('description', ''),
            owner=request.user,
            status='draft'
        )

        # Create nodes with ID mapping
        node_id_map = {}
        for node_data in workflow_data.get('nodes', []):
            node = Node.objects.create(
                workflow=workflow,
                node_type=node_data.get('type', 'llm'),
                name=node_data.get('name', 'Node'),
                position_x=node_data.get('position', {}).get('x', 0),
                position_y=node_data.get('position', {}).get('y', 0),
                config=node_data.get('config', {})
            )
            node_id_map[node_data['id']] = node.id

        # Create edges (skip invalid edges where source/target node was not found)
        for edge_data in workflow_data.get('edges', []):
            source_id = node_id_map.get(edge_data.get('source'))
            target_id = node_id_map.get(edge_data.get('target'))
            if source_id is None or target_id is None:
                continue  # Skip edges with missing nodes
            Edge.objects.create(
                workflow=workflow,
                source_node_id=source_id,
                target_node_id=target_id,
                label=edge_data.get('label', '')
            )

        # Update session
        session.workflow = workflow
        session.status = 'completed'
        session.messages.append({
            'role': 'system',
            'content': f'工作流已保存: {workflow.name}'
        })
        session.save()

        # Prefetch nodes/edges to avoid triggering RelatedManager during serialization
        prefetched_nodes = list(workflow.nodes.all())
        prefetched_edges = list(workflow.edges.all())
        node_serializer = NodeSerializer(prefetched_nodes, many=True)
        edge_serializer = EdgeSerializer(prefetched_edges, many=True)
        workflow_serializer = WorkflowDetailSerializer(
            workflow,
            context={
                'request': request,
                'nodes': node_serializer.data,
                'edges': edge_serializer.data,
            }
        )

        return Response({
            'workflow_id': workflow.id,
            'workflow_json': workflow_serializer.data,
            'workflow': workflow_serializer.data,  # Alias for backward compatibility
            'session_id': session.id,
            'status': session.status,
            'message': '工作流已保存'
        })


class NLWorkflowPreviewView(APIView):
    """Preview generated workflow without saving."""

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='10/m', method='POST', block=True))
    def post(self, request):
        """Preview workflow from description without saving."""
        description = request.data.get('description', '')
        model = request.data.get('model')
        temperature = float(request.data.get('temperature', DEFAULT_TEMPERATURE))

        if not description:
            return Response(
                {'error': ERROR_NO_DESCRIPTION},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            nl_service = get_nl_service_for_request(request, model=model, temperature=temperature)
            workflow_data = nl_service.generate_workflow(
                description,
                include_validation=True
            )

            if 'error' in workflow_data:
                return Response({
                    'error': workflow_data['error']
                }, status=status.HTTP_400_BAD_REQUEST)

            nodes = workflow_data.get('nodes', [])
            edges = workflow_data.get('edges', [])

            return Response({
                'preview': {
                    'name': workflow_data.get('name', 'Generated Workflow'),
                    'description': workflow_data.get('description', ''),
                    'nodes': nodes,
                    'edges': edges,
                    'node_count': len(nodes),
                    'edge_count': len(edges),
                },
                'workflow_json': workflow_data,
                'workflow': workflow_data,  # Alias for backward compatibility
                'validation': workflow_data.get('validation'),
                'message': '预览生成成功'
            })

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NLWorkflowStreamView(APIView):
    """
    Stream workflow generation for real-time UX.
    
    POST /api/v1/nl-workflow/stream/
    Body: { description, name?, model?, temperature? }
    
    Returns StreamingHttpResponse with Server-Sent Events (SSE).
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def post(self, request):
        """Generate workflow with streaming response."""
        description = request.data.get('description', '')
        name = request.data.get(
            'name',
            f'NL Workflow {NLSession.objects.filter(user=request.user).count() + 1}'
        )
        model = request.data.get('model')
        temperature = float(request.data.get('temperature', DEFAULT_TEMPERATURE))

        if not description:
            return Response(
                {'error': ERROR_NO_DESCRIPTION},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            nl_service = get_nl_service_for_request(request, model=model, temperature=temperature)
            
            # Create session for tracking
            session = NLSession.objects.create(
                user=request.user,
                name=name,
                description=description,
                status='processing',
                model_used=model or '',
                messages=[]
            )
            
            def generate_stream():
                """Generator for streaming response."""
                try:
                    # Yield session info
                    yield f"data: {json.dumps({'type': 'session', 'session_id': str(session.id)}, ensure_ascii=False)}\n\n"
                    
                    # Generate workflow with streaming
                    for chunk in nl_service.generate_workflow_streaming(description):
                        if isinstance(chunk, str):
                            chunk_data = json.loads(chunk)
                        else:
                            chunk_data = chunk
                        
                        # Format as SSE
                        yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                        
                        # If we got a workflow, update session
                        if chunk_data.get('type') == 'workflow':
                            workflow = chunk_data.get('workflow', {})
                            session.workflow_json = workflow
                            session.workflow_name = workflow.get('name', name)
                            session.status = 'completed'
                            session.messages.append({
                                'role': 'assistant',
                                'content': f'已生成工作流: {session.workflow_name}'
                            })
                            session.save()
                        elif chunk_data.get('type') == 'error':
                            session.status = 'failed'
                            session.error_message = chunk_data.get('error', 'Unknown error')
                            session.save()
                    
                except Exception as e:
                    import logging
                    logging.exception("Streaming generation failed")
                    session.status = 'failed'
                    session.error_message = str(e)
                    session.save()
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
            
            response = StreamingHttpResponse(
                generate_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except Exception as e:
            import logging
            logging.exception("Stream view failed")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NLWorkflowAnalyzeIntentView(APIView):
    """
    Analyze user intent from message.
    
    POST /api/v1/nl-workflow/analyze-intent/
    Body: { message }
    
    Returns intent type and extracted details.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Analyze user message intent."""
        message = request.data.get('message', '')

        if not message:
            return Response(
                {'error': ERROR_NO_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST
            )

        intent = analyze_intent(message)
        
        # Get intent details from service
        nl_service = get_nl_service_for_request(request)
        intent_details = nl_service._get_intent_details(message)
        
        return Response({
            'intent': intent,
            'details': intent_details,
            'message': message
        })


class NLWorkflowSuggestView(APIView):
    """
    Get workflow suggestions based on current workflow state.
    
    POST /api/v1/nl-workflow/suggest/
    Body: { workflow?, description? }
    
    Returns suggested modifications or next steps.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Get workflow suggestions."""
        workflow = request.data.get('workflow', {})
        description = request.data.get('description', '')

        nl_service = get_nl_service_for_request(request)
        
        if workflow:
            suggestions = nl_service._generate_suggestions(workflow)
        else:
            suggestions = nl_service._generate_suggestions_from_description(description)
        
        return Response({
            'suggestions': suggestions,
            'count': len(suggestions)
        })
