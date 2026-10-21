"""
Views for NL to Workflow.
Unifies API response format across all endpoints.
"""

import json
import uuid
from copy import deepcopy
from math import isfinite
from pathlib import Path
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings

try:
    from ratelimit.decorators import ratelimit
except ImportError:
    from django_ratelimit.decorators import ratelimit

from .models import NLSession
from .workspace import (read_workflow_draft, workflow_fingerprint, SESSION_PAGE_SIZE,
                        SESSION_PAGE_SIZE_MAX, SESSION_NAME_MAX_LENGTH, WORKSPACE_API_VERSION)
from .workflow_layout import auto_layout_workflow
from .services import get_nl_service, NLToWorkflowService, analyze_intent, get_email_config_guidance, get_node_config_guidance
from .constants import resolve_initial_stream_mode, normalize_request_mode
from workflows.models import Workflow, Node, Edge
from workflows.serializers import WorkflowDetailSerializer, NodeSerializer, EdgeSerializer
from config.constants import (
    DEFAULT_MAX_TOKENS,
    RATE_LIMIT_NL_EDITOR_APPLY,
    RATE_LIMIT_NL_PREVIEW,
    RATE_LIMIT_NL_STREAM,
    WORKFLOW_NODE_COLLISION_GAP_X,
    WORKFLOW_NODE_COLLISION_GAP_Y,
    WORKFLOW_NODE_DEFAULT_HEIGHT,
    WORKFLOW_NODE_DEFAULT_WIDTH,
)

import logging

logger = logging.getLogger(__name__)

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
MODEL_SITE_REQUIRED_FEATURES = [
    'imageRecognition',
    'videoRecognition',
    'realtimeRecognition',
    'factRecognition',
    'historyRecords',
]


def _default_yolo_dataset_path():
    configured = getattr(settings, 'NL_WORKFLOW_DEFAULT_YOLO_DATASET_PATH', '')
    if configured:
        return str(Path(configured).expanduser())
    return str(Path(settings.BASE_DIR) / 'scripts' / 'fixtures' / 't2_mini_yolo')


def _default_training_output_dir():
    root = Path(getattr(settings, 'NL_WORKFLOW_TRAINING_OUTPUT_ROOT', Path(settings.BASE_DIR) / 'outputs'))
    return str(root / f'nl_yolo_{uuid.uuid4().hex[:8]}')


def _default_site_output_dir():
    root = Path(getattr(settings, 'NL_WORKFLOW_SITE_OUTPUT_ROOT', Path(settings.MEDIA_ROOT) / 'generated' / 'nl_sites'))
    return str(root / f'site_{uuid.uuid4().hex[:8]}')


def _workflow_has_node_type(workflow_data, node_type):
    return any(
        isinstance(node, dict) and (node.get('type') or '').lower() == node_type
        for node in (workflow_data.get('nodes') or [])
    )


def _is_model_training_site_workflow(workflow_data):
    has_training = any(
        isinstance(node, dict) and (node.get('type') or '').lower() in {'yolo_training', 'model_training', 'clip_training', 'transformer_training'}
        for node in (workflow_data.get('nodes') or [])
    )
    return has_training and _workflow_has_node_type(workflow_data, 'website_generator')


def _derive_yolo_base_weight(config):
    explicit = config.get('base_weight_uri') or config.get('baseWeightUri') or config.get('baseModel')
    if explicit:
        return explicit
    yolo_version = str(config.get('yoloVersion') or 'v8').lower().replace(' ', '')
    variant = str(config.get('modelVariant') or 'n').lower().replace('.pt', '')
    if yolo_version in {'11', 'v11', 'yolo11'}:
        return f'yolo11{variant}.pt'
    if yolo_version.startswith('yolo') and not yolo_version.startswith('yolov'):
        return f'{yolo_version}{variant}.pt'
    version_number = yolo_version.replace('yolov', '').replace('v', '') or '8'
    return f'yolov{version_number}{variant}.pt'


def _merge_required_features(existing):
    features = list(existing or []) if isinstance(existing, list) else []
    for feature in MODEL_SITE_REQUIRED_FEATURES:
        if feature not in features:
            features.append(feature)
    return features


def _enrich_model_training_site_workflow(workflow_data):
    """Add executable defaults for NL-generated model-training site workflows."""
    if not isinstance(workflow_data, dict) or not _is_model_training_site_workflow(workflow_data):
        return workflow_data

    default_dataset_path = _default_yolo_dataset_path()
    training_output_dir = None
    site_output_dir = None

    for node in workflow_data.get('nodes') or []:
        if not isinstance(node, dict):
            continue
        node_type = (node.get('type') or '').lower()
        config = node.setdefault('config', {})
        if not isinstance(config, dict):
            config = {}
            node['config'] = config

        if node_type == 'dataset_upload':
            config.setdefault('format', 'yolo')
            config.setdefault('source', config.get('sourceType') or 'upload')
            config.setdefault('sourceType', config.get('source') or 'upload')
            if not any(config.get(key) for key in ('path', 'sourcePath', 'datasetPath', 'filePath')):
                config['path'] = default_dataset_path
                config['demoDataFallback'] = True
            config.setdefault('customPathEnabled', True)
            config.setdefault('description', 'YOLO dataset source. Users can replace path with their own dataset directory before execution.')

        elif node_type == 'yolo_training':
            config.setdefault('trainingMode', 'local')
            config.setdefault('yoloVersion', 'v8')
            config.setdefault('modelVariant', 'n')
            config.setdefault('epochs', 1)
            config.setdefault('batchSize', 2)
            config.setdefault('imageSize', 320)
            config.setdefault('dataSourceType', 'upstream')
            config.setdefault('device', 'cpu')
            config.setdefault('base_weight_uri', _derive_yolo_base_weight(config))
            config.setdefault('baseModel', config.get('base_weight_uri'))
            config.setdefault('datasetSource', {'mode': 'upstream', 'fromNodeType': 'dataset_upload'})
            training_output_dir = config.get('outputDir') or _default_training_output_dir()
            config.setdefault('outputDir', training_output_dir)
            runtime = config.setdefault('runtime', {})
            if isinstance(runtime, dict):
                runtime.setdefault('storagePath', training_output_dir)
                runtime.setdefault('customPathEnabled', True)

        elif node_type == 'website_generator':
            site_output_dir = config.get('outputDir') or _default_site_output_dir()
            config.setdefault('outputDir', site_output_dir)
            config.setdefault('websiteType', 'detection')
            config.setdefault('projectType', 'detection')
            config.setdefault('framework', 'ultralytics')
            config.setdefault('frontendFramework', 'vue')
            config.setdefault('backendFramework', 'flask')
            config.setdefault('dbEngine', 'mysql')
            config.setdefault('waitForCompletion', True)
            config['requiredFeatures'] = _merge_required_features(config.get('requiredFeatures') or config.get('required_features'))
            config.setdefault('agentMemoryEnabled', True)
            config.setdefault('selfCheckRequired', True)
            config.setdefault('siteBrief', {
                'stack': 'Flask + Vue + Mysql',
                'features': config['requiredFeatures'],
                'source': 'NL model-training workflow',
            })
            wizard = config.setdefault('wizard', {})
            if isinstance(wizard, dict):
                wizard.setdefault('siteName', '智能识别系统')
                wizard.setdefault('usageDescription', '支持图片识别、视频识别、实时识别、事实识别和历史记录。')
                wizard.setdefault('primaryColor', '#2563eb')
                wizard.setdefault('dbEngine', 'mysql')
                wizard.setdefault('websiteType', 'detection')
                wizard.setdefault('wizardCompleted', True)
            environment = config.setdefault('environmentConfig', {})
            if isinstance(environment, dict):
                environment.setdefault('dbEngine', 'mysql')
                environment.setdefault('outputDir', site_output_dir)
                environment.setdefault('customPathEnabled', True)

        elif node_type in {'backend_setup', 'frontend_setup', 'ui_beautify', 'site_code_review'}:
            config.setdefault('agentMode', 'auto')
            config.setdefault('waitForCompletion', True)
            if site_output_dir:
                config.setdefault('outputDir', site_output_dir)
        elif node_type == 'environment_provision':
            config.setdefault('runtimeMode', 'desktop')
            config.setdefault('dbEngine', 'mysql')
            config.setdefault('customPathEnabled', True)
            if site_output_dir:
                config.setdefault('outputDir', site_output_dir)
        elif node_type == 'site_qa':
            config.setdefault('websiteType', 'detection')
            config.setdefault('qaProfile', 'default')
            config.setdefault('runStaticChecks', True)
            config.setdefault('runApiChecks', True)
            config.setdefault('skipPlaywright', True)
            if site_output_dir:
                config.setdefault('outputDir', site_output_dir)
        elif node_type == 'site_preview':
            config.setdefault('qaProfile', 'default')
            if site_output_dir:
                config.setdefault('outputDir', site_output_dir)
        elif node_type == 'project_agent':
            config.setdefault('autoQaAfterEdit', True)
            config.setdefault('memoryEnabled', True)
            config.setdefault('syncKnowledgeBase', True)
            if site_output_dir:
                config.setdefault('outputDir', site_output_dir)

    return workflow_data


def _coerce_canvas_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number):
        return None
    return number


def _finite_node_position(node_data):
    position = node_data.get('position') if isinstance(node_data, dict) else None
    if not isinstance(position, dict):
        return None
    x = _coerce_canvas_number(position.get('x'))
    y = _coerce_canvas_number(position.get('y'))
    if x is None or y is None:
        return None
    return {'x': x, 'y': y}


def _rects_overlap(a, b):
    return (
        a['x'] < b['right'] + WORKFLOW_NODE_COLLISION_GAP_X
        and a['right'] + WORKFLOW_NODE_COLLISION_GAP_X > b['x']
        and a['y'] < b['bottom'] + WORKFLOW_NODE_COLLISION_GAP_Y
        and a['bottom'] + WORKFLOW_NODE_COLLISION_GAP_Y > b['y']
    )


def _workflow_positions_need_layout(workflow_data):
    nodes = workflow_data.get('nodes') or []
    rects = []
    for node_data in nodes:
        position = _finite_node_position(node_data)
        if position is None:
            return True

        rect = {
            'x': position['x'],
            'y': position['y'],
            'right': position['x'] + WORKFLOW_NODE_DEFAULT_WIDTH,
            'bottom': position['y'] + WORKFLOW_NODE_DEFAULT_HEIGHT,
        }
        if any(_rects_overlap(rect, existing) for existing in rects):
            return True
        rects.append(rect)

    return False


def _unique_workflow_node_id(nodes, preferred_id):
    existing = {str(node.get('id')) for node in nodes if isinstance(node, dict) and node.get('id')}
    if preferred_id not in existing:
        return preferred_id
    index = 1
    while f'{preferred_id}_{index}' in existing:
        index += 1
    return f'{preferred_id}_{index}'


def _edge_exists(edges, source, target):
    return any(
        str(edge.get('source') or '') == str(source)
        and str(edge.get('target') or '') == str(target)
        for edge in edges
        if isinstance(edge, dict)
    )


def _append_workflow_edge(edges, source, target, label=''):
    if not source or not target or source == target or _edge_exists(edges, source, target):
        return
    edges.append({
        'id': f'edge_{source}_{target}',
        'source': source,
        'target': target,
        'label': label,
    })


def _ensure_workflow_boundaries(workflow_data):
    """Ensure confirmed NL workflows have executable start/end boundaries."""
    if not isinstance(workflow_data, dict):
        return workflow_data

    nodes = [node for node in (workflow_data.get('nodes') or []) if isinstance(node, dict)]
    edges = [edge for edge in (workflow_data.get('edges') or []) if isinstance(edge, dict)]
    if not nodes:
        workflow_data['nodes'] = nodes
        workflow_data['edges'] = edges
        return workflow_data

    start_nodes = [node for node in nodes if (node.get('type') or '').lower() == 'start']
    end_nodes = [node for node in nodes if (node.get('type') or '').lower() == 'end']

    if start_nodes:
        start_node = start_nodes[0]
    else:
        start_node = {
            'id': _unique_workflow_node_id(nodes, 'flowly_start'),
            'type': 'start',
            'name': '开始',
            'config': {},
        }
        nodes.insert(0, start_node)

    if end_nodes:
        end_node = end_nodes[0]
    else:
        end_node = {
            'id': _unique_workflow_node_id(nodes, 'flowly_end'),
            'type': 'end',
            'name': '结束',
            'config': {},
        }
        nodes.append(end_node)

    node_ids = {str(node.get('id')) for node in nodes if node.get('id')}
    start_id = str(start_node.get('id'))
    end_id = str(end_node.get('id'))
    incoming = {node_id: 0 for node_id in node_ids}
    outgoing = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        source = str(edge.get('source') or '')
        target = str(edge.get('target') or '')
        if source in node_ids and target in node_ids:
            outgoing[source] = outgoing.get(source, 0) + 1
            incoming[target] = incoming.get(target, 0) + 1

    business_ids = [
        str(node.get('id'))
        for node in nodes
        if str(node.get('id')) not in {start_id, end_id}
    ]
    root_ids = [node_id for node_id in business_ids if incoming.get(node_id, 0) == 0]
    leaf_ids = [node_id for node_id in business_ids if outgoing.get(node_id, 0) == 0]
    if not root_ids and business_ids:
        root_ids = [business_ids[0]]
    if not leaf_ids and business_ids:
        leaf_ids = [business_ids[-1]]

    for root_id in root_ids:
        _append_workflow_edge(edges, start_id, root_id)
    for leaf_id in leaf_ids:
        _append_workflow_edge(edges, leaf_id, end_id)

    workflow_data['nodes'] = nodes
    workflow_data['edges'] = edges
    return workflow_data


def _prepare_workflow_positions_for_save(workflow_data):
    """Preserve valid positions, and layout only missing/invalid/colliding graphs."""
    if not isinstance(workflow_data, dict):
        return workflow_data

    prepared = deepcopy(workflow_data)
    prepared = _ensure_workflow_boundaries(prepared)
    prepared = _enrich_model_training_site_workflow(prepared)
    if _workflow_positions_need_layout(prepared):
        prepared = auto_layout_workflow(prepared)
    return prepared


def _normalize_rate_limit(rate: str) -> str:
    """Normalize config rate strings for django-ratelimit (e.g. 5/minute → 5/m)."""
    return rate.replace('/minute', '/m').replace('minute', 'm')


NL_STREAM_RATE = _normalize_rate_limit(
    getattr(settings, 'NL_WORKFLOW_STREAM_RATE', None)
    or (RATE_LIMIT_NL_STREAM if not getattr(settings, 'DEBUG', False) else '20/m')
)
NL_PREVIEW_RATE = _normalize_rate_limit(
    getattr(settings, 'NL_WORKFLOW_PREVIEW_RATE', None) or RATE_LIMIT_NL_PREVIEW
)
NL_EDITOR_APPLY_RATE = _normalize_rate_limit(
    getattr(settings, 'NL_WORKFLOW_EDITOR_APPLY_RATE', None)
    or (RATE_LIMIT_NL_EDITOR_APPLY if not getattr(settings, 'DEBUG', False) else '60/m')
)


def _sse_data(payload):
    """Serialize SSE payload with explicit UTF-8 encoding safety."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _resolve_current_workflow(request, session):
    """Prefer editor-provided workflow snapshot, fallback to session state."""
    incoming = request.data.get('workflow') or request.data.get('workflow_json')
    if isinstance(incoming, dict) and incoming.get('nodes'):
        return incoming
    if session.workflow_json and session.workflow_json.get('nodes'):
        return session.workflow_json
    return None


def _yield_conversation_stream_events(nl_service, session, user_message, prior_messages, mode=None):
    """Stream SSE events for continue_conversation (chat, modify, or generate)."""
    current_workflow = session.workflow_json if session.workflow_json else None
    assistant_content = ''
    workflow = None
    suggestions = []
    changes = []
    intent = 'chat'
    ready_to_generate = False

    for chunk in nl_service.continue_conversation_streaming(
        prior_messages,
        user_message,
        current_workflow=current_workflow,
        mode=mode,
        existing_summary=getattr(session, 'conversation_summary', '') or '',
        session_id=str(session.id),
    ):
        if isinstance(chunk, str):
            chunk_data = json.loads(chunk)
        else:
            chunk_data = chunk

        chunk_type = chunk_data.get('type')

        if chunk_type == 'intent':
            intent = chunk_data.get('intent', intent)
            yield _sse_data(chunk_data)
            continue

        if chunk_type == 'token':
            assistant_content += chunk_data.get('content', '')
            yield _sse_data(chunk_data)
            continue

        if chunk_type == 'summary':
            summary = chunk_data.get('conversation_summary') or ''
            if summary:
                session.conversation_summary = summary
                session.save(update_fields=['conversation_summary', 'updated_at'])
            yield _sse_data(chunk_data)
            continue

        if chunk_type == 'workflow':
            workflow = chunk_data.get('workflow')
            if workflow:
                session.workflow_json = workflow
                session.workflow_name = workflow.get('name', session.workflow_name)
                session.workflow = None
                session.save()
            yield _sse_data(chunk_data)
            continue

        if chunk_type == 'progress':
            yield _sse_data(chunk_data)
            continue

        if chunk_type == 'error':
            session.status = 'failed'
            session.error_message = chunk_data.get('error', 'Unknown error')
            session.save()
            yield _sse_data(chunk_data)
            return

        if chunk_type == 'done':
            assistant_content = chunk_data.get('message') or assistant_content
            workflow = chunk_data.get('workflow') or workflow
            suggestions = chunk_data.get('suggestions', [])
            changes = chunk_data.get('changes', [])
            intent = chunk_data.get('intent', intent)
            ready_to_generate = chunk_data.get('ready_to_generate', False)

            if workflow:
                session.workflow_json = workflow
                session.workflow_name = workflow.get('name', session.workflow_name)
                session.workflow = None

                email_guidance = get_email_config_guidance(workflow)
                if email_guidance:
                    yield _sse_data({'type': 'email_guidance', 'email_guidance': email_guidance})

                node_guidance = get_node_config_guidance(workflow)
                if node_guidance:
                    yield _sse_data({'type': 'node_guidance', 'node_guidance': node_guidance})

            session.messages.append({'role': 'assistant', 'content': assistant_content})
            session.status = 'completed'
            session.save()

            if suggestions:
                yield _sse_data({'type': 'suggestions', 'suggestions': suggestions})
            if changes:
                yield _sse_data({'type': 'changes', 'changes': changes})
            if ready_to_generate:
                yield _sse_data({'type': 'ready_to_generate', 'ready_to_generate': True})

            yield _sse_data({
                'type': 'done',
                'message': assistant_content,
                'workflow': workflow,
                'intent': intent,
                'ready_to_generate': ready_to_generate,
                'progress': 100,
            })
            return

        # Pass through other event types (suggestions, email_guidance, node_guidance, etc.)
        yield _sse_data(chunk_data)


def get_nl_service_for_request(request, model=None, temperature=DEFAULT_TEMPERATURE, mode=None):
    """Create an NL service configured for the current request."""
    request_mode = normalize_request_mode(mode) or 'chat'
    if request_mode == 'generate':
        max_tokens = int(getattr(settings, 'NL_GENERATE_MAX_TOKENS', DEFAULT_MAX_TOKENS))
    elif request_mode == 'editor':
        max_tokens = int(getattr(settings, 'NL_EDITOR_MAX_TOKENS', 2048))
    else:
        max_tokens = int(getattr(settings, 'NL_CHAT_MAX_TOKENS', 512))
    service = get_nl_service(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        user=request.user
    )
    caps = request.data.get('client_capabilities') or request.data.get('clientCapabilities')
    if caps:
        service.client_capabilities = caps
    return service


def _build_session_response(session, include_workflow=False):
    """Build a consistent session response dict."""
    workflow_json = session.workflow_json or {}
    # Compute guidance for old sessions that don't have it stored
    if workflow_json.get('nodes'):
        if '_node_guidance' not in workflow_json:
            node_guidance = get_node_config_guidance(workflow_json)
            if node_guidance:
                workflow_json = dict(workflow_json)
                workflow_json['_node_guidance'] = node_guidance
        if '_email_guidance' not in workflow_json:
            email_guidance = get_email_config_guidance(workflow_json)
            if email_guidance:
                workflow_json = dict(workflow_json)
                workflow_json['_email_guidance'] = email_guidance

    data = {
        'workspace_version': WORKSPACE_API_VERSION,
        'session_id': session.id,
        'name': session.name,
        'description': session.description,
        'workflow_id': session.workflow_id,
        'workflow_json': workflow_json,
        'workflow_name': session.workflow_name,
        'status': session.status,
        'error_message': session.error_message or None,
        'messages': session.messages,
        'conversation_summary': getattr(session, 'conversation_summary', '') or '',
        'celery_task_id': getattr(session, 'celery_task_id', '') or '',
        'node_count': len(workflow_json.get('nodes', [])),
        'edge_count': len(workflow_json.get('edges', [])),
        'created_at': session.created_at,
        'updated_at': session.updated_at,
    }
    if include_workflow and workflow_json:
        data['workflow'] = workflow_json
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
        include_all = str(request.query_params.get('include_all', '')).lower() in ('1', 'true', 'yes')
        if not include_all:
            agnes_models = [
                m for m in models
                if 'agnes' in str(m.get('model_id', '')).lower()
                or str(m.get('provider', '')).lower() == 'agnes'
            ]
            if agnes_models:
                models = agnes_models
        default_model = service._resolve_model() or (models[0]['model_id'] if models else None)
        if default_model and not any(m.get('model_id') == default_model for m in models):
            default_model = models[0]['model_id'] if models else default_model
        return Response({
            'models': models,
            'default': default_model,
            'count': len(models),
            'scope': 'all' if include_all else 'agnes_default',
        })


class NLSessionViewSet(APIView):
    """ViewSet for NL sessions - handles list and create."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's NL sessions."""
        sessions = NLSession.objects.filter(user=request.user).order_by('-updated_at', '-id')
        query = request.query_params.get('search', '').strip()
        if query:
            sessions = sessions.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(workflow_name__icontains=query))
        session_status = request.query_params.get('status', '')
        if session_status:
            sessions = sessions.filter(status=session_status)
        if request.query_params.get('paginated') == 'true':
            try:
                page = max(1, int(request.query_params.get('page', 1)))
                page_size = min(SESSION_PAGE_SIZE_MAX, max(1, int(request.query_params.get('page_size', SESSION_PAGE_SIZE))))
            except (ValueError, TypeError):
                return Response({'error': '分页参数必须是整数'}, status=status.HTTP_400_BAD_REQUEST)
            count = sessions.count()
            offset = (page - 1) * page_size
            return Response({'results': [_build_session_list_item(s) for s in sessions[offset:offset + page_size]],
                             'count': count, 'page': page, 'has_more': offset + page_size < count})
        sessions = sessions[:SESSION_PAGE_SIZE]
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
        mode = request.data.get('mode')

        if not description:
            return Response(
                {'error': ERROR_NO_DESCRIPTION},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = NLSession.objects.create(
            user=request.user,
            name=name,
            description=description,
            messages=[{'role': 'user', 'content': description}],
        )

        try:
            # This endpoint is the legacy "create session and generate workflow"
            # API. Keep open-ended thinking/chat behavior opt-in so callers that
            # expect a workflow JSON are not routed into a conversational branch.
            stream_mode = normalize_request_mode(mode) or 'generate'
            nl_service = get_nl_service_for_request(
                request, model=model, temperature=temperature, mode=stream_mode
            )

            if stream_mode == 'chat':
                response = nl_service.continue_conversation(
                    [], description, current_workflow=None, mode=mode
                )
                session.messages.append({
                    'role': 'assistant',
                    'content': response.get('message', ''),
                })
                session.status = 'completed'
                session.save()
                return Response({
                    'session_id': session.id,
                    'id': session.id,
                    'workflow_json': response.get('workflow'),
                    'workflow': response.get('workflow'),
                    'status': session.status,
                    'message': response.get('message', ''),
                    'suggestions': response.get('suggestions', []),
                    'intent': response.get('intent', 'chat'),
                    'ready_to_generate': response.get('ready_to_generate', False),
                })

            logger.info(f"NL service created, model={model}")

            # Async path: enqueue Celery when requested or globally enabled
            async_raw = request.data.get('async')
            use_async = (
                async_raw is True
                or str(async_raw).lower() in ('1', 'true', 'yes')
                or getattr(settings, 'NL_WORKFLOW_ASYNC_GENERATE', False)
            )
            if use_async:
                from .task_sync import enqueue_generate_for_session

                task_id = enqueue_generate_for_session(
                    session, model=model, temperature=temperature
                )
                return Response({
                    'session_id': session.id,
                    'id': session.id,
                    'status': 'processing',
                    'async': True,
                    'task_id': task_id,
                    'message': '工作流正在后台生成，请轮询任务状态',
                }, status=status.HTTP_202_ACCEPTED)

            workflow_data = nl_service.generate_workflow(
                description,
                context={'session_id': str(session.id), 'user_id': request.user.id},
            )
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
            session.status = 'completed'
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
                'message': '工作流生成成功',
                'email_guidance': workflow_data.get('_email_guidance'),
            })

        except Exception as e:
            session.status = 'failed'
            session.error_message = str(e)
            session.save()
            logger.exception(f"NL workflow generation failed: {e}")
            return Response({
                'session_id': session.id,
                'error': '生成工作流时遇到了问题，请重试',
                'status': 'failed',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    @transaction.atomic
    def patch(self, request, session_id):
        """Update session (rename, etc.)."""
        try:
            session = NLSession.objects.select_for_update().get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        name = request.data.get('name')
        if 'name' in request.data:
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > SESSION_NAME_MAX_LENGTH:
                return Response(
                    {'error': '会话名称不能为空，且不能超过 200 个字符'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            session.name = name.strip()
        if 'workflow_json' in request.data:
            if session.status == 'processing':
                return Response({'error': '任务处理中，请完成后再编辑'}, status=status.HTTP_409_CONFLICT)
            session.workflow_json = read_workflow_draft(request.data['workflow_json'])
            session.workflow_json.pop('_node_guidance', None)
            session.workflow_json.pop('_email_guidance', None)
            session.workflow_name = session.workflow_json.get('name', session.workflow_name)
            # Keep the last message and editable draft consistent when reopening history.
            messages = deepcopy(session.messages)
            for message in reversed(messages):
                if message.get('role') == 'assistant' and message.get('workflow'):
                    message['workflow'] = session.workflow_json
                    break
            session.messages = messages
        session.save(update_fields=['name', 'workflow_json', 'workflow_name', 'messages', 'updated_at'])

        return Response({**_build_session_response(session, include_workflow=True), 'message': '会话已更新'})


class NLSessionTaskStatusView(APIView):
    """Poll async NL generate / conversation task status."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = NLSession.objects.get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )

        from .task_sync import reconcile_session_with_celery

        reconcile = reconcile_session_with_celery(session)
        session.refresh_from_db()

        task_id = session.celery_task_id or request.query_params.get('task_id') or ''
        payload = {
            'session_id': session.id,
            'status': session.status,
            'task_id': task_id,
            'workflow_name': session.workflow_name,
            'error_message': session.error_message or None,
            'conversation_summary': session.conversation_summary or '',
            'async': session.status == 'processing',
            'recovered': reconcile.get('recovered', False),
        }

        if session.status == 'completed':
            payload['workflow_json'] = session.workflow_json
            payload['workflow'] = session.workflow_json
            payload['message'] = f"已生成工作流: {session.workflow_name}" if session.workflow_name else '完成'
        elif session.status == 'failed':
            payload['message'] = session.error_message or '生成失败'
        else:
            payload['message'] = '处理中'

        payload['celery_state'] = reconcile.get('celery_state')
        if task_id and not payload.get('celery_state'):
            try:
                from celery.result import AsyncResult
                payload['celery_state'] = AsyncResult(task_id).state
            except Exception as exc:
                logger.debug('celery status lookup failed: %s', exc)
                payload['celery_state'] = 'UNKNOWN'

        return Response(payload)

    def post(self, request, session_id):
        """Retry / re-enqueue generation for a stuck or failed session."""
        try:
            session = NLSession.objects.get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND,
            )

        action = (request.data.get('action') or 'retry').strip().lower()
        if action not in ('retry', 'requeue'):
            return Response({'error': '不支持的操作'}, status=status.HTTP_400_BAD_REQUEST)

        if (session.workflow_json or {}).get('nodes') and session.status == 'completed':
            return Response({
                'session_id': session.id,
                'status': 'completed',
                'message': '会话已完成，无需重试',
                'workflow_json': session.workflow_json,
                'workflow': session.workflow_json,
            })

        from .task_sync import enqueue_generate_for_session, reconcile_session_with_celery

        # First try to recover a finished-but-unsynced task
        reconcile = reconcile_session_with_celery(session)
        session.refresh_from_db()
        if session.status == 'completed' and (session.workflow_json or {}).get('nodes'):
            return Response({
                'session_id': session.id,
                'status': 'completed',
                'recovered': True,
                'message': '已从后台任务结果恢复工作流',
                'workflow_json': session.workflow_json,
                'workflow': session.workflow_json,
            })

        model = request.data.get('model') or session.model_used or None
        temperature = request.data.get('temperature')
        temperature = float(temperature) if temperature is not None else None
        task_id = enqueue_generate_for_session(session, model=model, temperature=temperature)
        return Response({
            'session_id': session.id,
            'status': 'processing',
            'async': True,
            'task_id': task_id,
            'requeued': True,
            'prior_reconcile': reconcile,
            'message': '已重新排队生成任务',
        }, status=status.HTTP_202_ACCEPTED)


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
        mode = request.data.get('mode')

        if not user_message:
            return Response(
                {'error': ERROR_NO_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_msg_index = len(session.messages)
        session.messages.append({
            'role': 'user',
            'content': user_message
        })
        session.save()

        try:
            nl_service = get_nl_service_for_request(
                request, model=model, temperature=temperature, mode=mode
            )
            current_workflow = _resolve_current_workflow(request, session)
            if current_workflow:
                session.workflow_json = current_workflow
                session.save()

            # Optional async continue for heavy generate turns
            async_raw = request.data.get('async')
            use_async = (
                async_raw is True
                or str(async_raw).lower() in ('1', 'true', 'yes')
            )
            request_mode = normalize_request_mode(mode)
            if use_async and request_mode == 'generate':
                from .tasks import continue_conversation_async

                session.status = 'processing'
                session.save(update_fields=['status', 'updated_at'])
                # Roll back optimistic user message append — task will re-append
                session.messages = session.messages[:user_msg_index]
                session.save(update_fields=['messages', 'updated_at'])
                async_result = continue_conversation_async.delay(
                    str(session.id),
                    user_message,
                    mode=mode,
                    model=model,
                )
                session.celery_task_id = async_result.id or ''
                session.save(update_fields=['celery_task_id', 'updated_at'])
                return Response({
                    'session_id': session.id,
                    'status': 'processing',
                    'async': True,
                    'task_id': session.celery_task_id,
                    'message': '正在后台生成，请轮询任务状态',
                }, status=status.HTTP_202_ACCEPTED)

            response = nl_service.continue_conversation(
                session.messages[:-1],
                user_message,
                current_workflow=current_workflow,
                mode=mode,
                existing_summary=session.conversation_summary or '',
                session_id=str(session.id),
            )

            session.messages.append({
                'role': 'assistant',
                'content': response.get('message', '')
            })

            # If workflow was modified, update session
            if response.get('workflow'):
                session.workflow_json = response['workflow']
                session.workflow_name = response['workflow'].get('name', session.workflow_name)
                # 清除旧的已保存工作流关联，确保 confirm 保存的是最新生成的工作流
                session.workflow = None

            if response.get('conversation_summary'):
                session.conversation_summary = response['conversation_summary']

            session.save()

            return Response({
                'message': response.get('message', ''),
                'suggestions': response.get('suggestions', []),
                'workflow_json': response.get('workflow'),
                'workflow': response.get('workflow'),  # Alias for backward compatibility
                'changes': response.get('changes', []),
                'intent': response.get('intent', 'chat'),
                'ready_to_generate': response.get('ready_to_generate', False),
                'conversation_summary': session.conversation_summary or '',
                'email_guidance': get_email_config_guidance(response.get('workflow', {})) if response.get('workflow') else None,
                'node_guidance': get_node_config_guidance(response.get('workflow', {})) if response.get('workflow') else None,
            })

        except Exception as e:
            # Roll back the user message we just appended
            session.messages = session.messages[:user_msg_index]
            session.status = 'failed'
            session.error_message = str(e)
            session.save()
            logger.exception(f"NL message stream failed: {e}")
            return Response({
                'session_id': session.id,
                'error': '生成回复时遇到了问题，请重试',
                'status': 'failed',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NLSessionMessageStreamView(APIView):
    """
    Stream message response for NL session.
    
    POST /api/v1/nl-workflow/sessions/<uuid:session_id>/message/stream/
    Body: { message, model?, temperature? }
    
    Returns StreamingHttpResponse with Server-Sent Events (SSE).
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate=NL_STREAM_RATE, method='POST', block=True))
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
        mode = request.data.get('mode')

        if not user_message:
            return Response(
                {'error': ERROR_NO_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST
            )

        session.messages.append({
            'role': 'user',
            'content': user_message
        })
        session.save()

        current_workflow = _resolve_current_workflow(request, session)
        if current_workflow:
            session.workflow_json = current_workflow
            session.save()

        def generate_stream():
            """Generator for streaming response."""
            try:
                nl_service = get_nl_service_for_request(
                    request, model=model, temperature=temperature, mode=mode
                )

                for event in _yield_conversation_stream_events(
                    nl_service,
                    session,
                    user_message,
                    session.messages[:-1],
                    mode=mode,
                ):
                    yield event
            except Exception as e:
                logger.exception("Streaming message failed")
                yield _sse_data({'type': 'error', 'error': str(e)})
        
        response = StreamingHttpResponse(
            generate_stream(),
            content_type='text/event-stream; charset=utf-8'
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
            session = NLSession.objects.select_for_update().get(id=session_id, user=request.user)
        except NLSession.DoesNotExist:
            return Response(
                {'error': ERROR_SESSION_NOT_FOUND},
                status=status.HTTP_404_NOT_FOUND
            )

        supplied = request.data.get('workflow_json')
        draft = read_workflow_draft(supplied) if supplied is not None else session.workflow_json
        if not draft:
            return Response(
                {'error': ERROR_NO_WORKFLOW},
                status=status.HTTP_400_BAD_REQUEST
            )

        fingerprint = workflow_fingerprint(draft)
        saved_fingerprint = next((m.get('workflow_fingerprint') for m in reversed(session.messages)
                                  if m.get('workflow_fingerprint')), None)
        reuse_saved = saved_fingerprint == fingerprint or (saved_fingerprint is None and supplied is None)
        if session.workflow_id and reuse_saved:
            prefetched_workflow = Workflow.objects.prefetch_related('nodes', 'edges').filter(
                id=session.workflow_id,
                owner=request.user
            ).first()
            if prefetched_workflow:
                node_serializer = NodeSerializer(list(prefetched_workflow.nodes.all()), many=True)
                edge_serializer = EdgeSerializer(list(prefetched_workflow.edges.all()), many=True)
                workflow_serializer = WorkflowDetailSerializer(
                    prefetched_workflow,
                    context={
                        'request': request,
                        'nodes': node_serializer.data,
                        'edges': edge_serializer.data,
                    }
                )
                return Response({
                    'workflow_id': prefetched_workflow.id,
                    'workflow_json': workflow_serializer.data,
                    'workflow': workflow_serializer.data,
                    'session_id': session.id,
                    'status': session.status,
                    'message': '工作流已保存'
                })

        workflow_data = _prepare_workflow_positions_for_save(read_workflow_draft(draft))
        session.workflow_json = draft
        session.workflow_name = draft.get('name', session.workflow_name)

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
            position = _finite_node_position(node_data) or {'x': 0, 'y': 0}
            node = Node.objects.create(
                workflow=workflow,
                node_type=node_data.get('type', 'llm'),
                name=node_data.get('name', 'Node'),
                # 不使用 LLM 生成的位置，让前端 Editor 加载时自动布局
                # 否则 NL 生成的随机位置会导致节点重叠
                position_x=position['x'],
                position_y=position['y'],
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
            'content': f'工作流已保存: {workflow.name}',
            'workflow_fingerprint': fingerprint
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

    @method_decorator(ratelimit(key='user', rate=NL_PREVIEW_RATE, method='POST', block=True))
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
            nl_service = get_nl_service_for_request(
                request, model=model, temperature=temperature, mode='generate'
            )
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
                'message': '预览生成成功',
                'email_guidance': workflow_data.get('_email_guidance'),
            })

        except Exception as e:
            logger.exception(f"NL preview failed: {e}")
            return Response({
                'error': '预览生成时遇到了问题，请重试'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NLEditorApplyView(APIView):
    """
    Synchronous editor assistant actions (layout / template modify / editor chat).

    POST /api/v1/nl-workflow/editor/apply/
    Body: { message, workflow, mode?, model?, temperature? }

    Used by the workflow editor assistant to avoid SSE stream rate limits for
    deterministic canvas updates.
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate=NL_EDITOR_APPLY_RATE, method='POST', block=True))
    def post(self, request):
        user_message = request.data.get('message', '')
        workflow = request.data.get('workflow') or request.data.get('workflow_json')
        model = request.data.get('model')
        temperature = float(request.data.get('temperature', DEFAULT_TEMPERATURE))
        mode = request.data.get('mode', 'editor')

        if not user_message:
            return Response(
                {'error': ERROR_NO_MESSAGE},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not isinstance(workflow, dict) or not workflow.get('nodes'):
            return Response(
                {'error': '请提供当前画布工作流'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            nl_service = get_nl_service_for_request(
                request, model=model, temperature=temperature, mode=mode
            )
            result = nl_service.continue_conversation(
                [],
                user_message,
                current_workflow=workflow,
                mode=mode,
            )
            response_workflow = result.get('workflow')
            return Response({
                'message': result.get('message', ''),
                'workflow': response_workflow,
                'workflow_json': response_workflow,
                'suggestions': result.get('suggestions', []),
                'changes': result.get('changes', []),
                'intent': result.get('intent', 'modify'),
                'ready_to_generate': result.get('ready_to_generate', False),
                'node_guidance': result.get('node_guidance'),
            })
        except Exception as e:
            logger.exception('NL editor apply failed: %s', e)
            return Response(
                {'error': '处理请求时遇到了问题，请重试'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NLWorkflowStreamView(APIView):
    """
    Stream workflow generation for real-time UX.
    
    POST /api/v1/nl-workflow/stream/
    Body: { description, name?, model?, temperature? }
    
    Returns StreamingHttpResponse with Server-Sent Events (SSE).
    """

    permission_classes = [IsAuthenticated]

    @method_decorator(ratelimit(key='user', rate=NL_STREAM_RATE, method='POST', block=True))
    def post(self, request):
        """Generate workflow with streaming response."""
        description = request.data.get('description', '')
        name = request.data.get(
            'name',
            f'NL Workflow {NLSession.objects.filter(user=request.user).count() + 1}'
        )
        model = request.data.get('model')
        temperature = float(request.data.get('temperature', DEFAULT_TEMPERATURE))
        existing_workflow = request.data.get('workflow') or request.data.get('workflow_json')
        mode = request.data.get('mode')

        if not description:
            return Response(
                {'error': ERROR_NO_DESCRIPTION},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            has_workflow = (
                isinstance(existing_workflow, dict)
                and existing_workflow.get('nodes')
            )
            stream_mode = resolve_initial_stream_mode(
                description,
                has_workflow=has_workflow,
                prior_messages=[],
                explicit_mode=mode,
            )
            nl_service = get_nl_service_for_request(
                request, model=model, temperature=temperature, mode=stream_mode
            )
            
            # Create session for tracking
            session = NLSession.objects.create(
                user=request.user,
                name=name,
                description=description,
                status='processing',
                model_used=model or '',
                messages=[{'role': 'user', 'content': description}],
                workflow_json=(
                    existing_workflow
                    if isinstance(existing_workflow, dict) and existing_workflow.get('nodes')
                    else {}
                ),
                workflow_name=(
                    (existing_workflow or {}).get('name', name)
                    if isinstance(existing_workflow, dict) and existing_workflow.get('nodes')
                    else name
                ),
            )
            
            def generate_stream():
                """Generator for streaming response."""
                try:
                    yield _sse_data({'type': 'session', 'session_id': str(session.id)})

                    has_workflow = (
                        isinstance(existing_workflow, dict)
                        and existing_workflow.get('nodes')
                    )

                    if has_workflow:
                        for event in _yield_conversation_stream_events(
                            nl_service,
                            session,
                            description,
                            [],
                            mode=mode,
                        ):
                            yield event
                        return

                    stream_mode = resolve_initial_stream_mode(
                        description,
                        has_workflow=False,
                        prior_messages=[],
                        explicit_mode=mode,
                    )

                    if stream_mode == 'chat':
                        for event in _yield_conversation_stream_events(
                            nl_service,
                            session,
                            description,
                            [],
                            mode=mode,
                        ):
                            yield event
                        return

                    # Generate workflow with streaming from scratch
                    assistant_saved = False
                    gen_context = {
                        'session_id': str(session.id),
                        'user_id': request.user.id,
                    }
                    for chunk in nl_service.generate_workflow_streaming(
                        description, context=gen_context
                    ):
                        if isinstance(chunk, str):
                            chunk_data = json.loads(chunk)
                        else:
                            chunk_data = chunk

                        yield _sse_data(chunk_data)

                        if chunk_data.get('type') == 'workflow':
                            workflow = chunk_data.get('workflow', {})
                            session.workflow_json = workflow
                            session.workflow_name = workflow.get('name', name)
                            session.status = 'completed'
                            if not assistant_saved:
                                session.messages.append({
                                    'role': 'assistant',
                                    'content': f'已生成工作流: {session.workflow_name}',
                                })
                                assistant_saved = True
                            session.save()
                        elif chunk_data.get('type') == 'done':
                            workflow = chunk_data.get('workflow')
                            if workflow:
                                session.workflow_json = workflow
                                session.workflow_name = workflow.get('name', name)
                            msg = chunk_data.get('message') or f'已生成工作流: {session.workflow_name}'
                            if not assistant_saved:
                                session.messages.append({'role': 'assistant', 'content': msg})
                                assistant_saved = True
                            session.status = 'completed'
                            session.save()
                        elif chunk_data.get('type') == 'error':
                            session.status = 'failed'
                            session.error_message = chunk_data.get('error', 'Unknown error')
                            session.save()

                except Exception as e:
                    logger.exception("Streaming generation failed")
                    session.status = 'failed'
                    session.error_message = str(e)
                    session.save()
                    yield _sse_data({'type': 'error', 'error': str(e)})
            
            response = StreamingHttpResponse(
                generate_stream(),
                content_type='text/event-stream'
            )
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response
            
        except Exception as e:
            logger.exception("Stream view failed")
            return Response({
                'error': '流式生成时遇到了问题，请重试'
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
        resolved = nl_service.resolve_intent(message)
        intent_details = nl_service._get_intent_details(message)
        
        return Response({
            'intent': resolved.get('intent', intent.get('intent')),
            'subtype': resolved.get('subtype', intent.get('subtype')),
            'source': resolved.get('source', 'keyword'),
            'confidence': resolved.get('confidence'),
            'ready_to_generate': resolved.get('ready_to_generate', False),
            'details': intent_details,
            'resolved': resolved,
            'keyword': intent,
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
