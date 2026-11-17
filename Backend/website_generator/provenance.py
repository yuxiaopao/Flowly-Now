"""Trusted execution provenance and a credential-free, authorized graph copy."""
import copy
import hashlib
from pathlib import Path
from uuid import UUID

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from tenants.models import TenantMembership
from .models import GeneratedSite, SiteWorkflowRebuild

ACTIVE_TEAM_STATUSES = ('active', 'trial')
MANIFEST_KEYS = ('schemaVersion', 'trainingJobId', 'trainingKind', 'modelType', 'taskType', 'framework', 'baseModel',
    'bestWeightPath', 'lastWeightPath', 'modelPath', 'labels', 'classNames', 'metrics', 'inputShape', 'imageSize',
    'embeddingModel', 'indexDir', 'artifactUri', 'capabilities', 'metricHistory', 'previewSamples', 'exportedArtifacts', 'siteHints')
COPY_NOTICE = '副本保留模型权重、站点用途和界面配置；使用新的输出目录，不复制数据库连接、密码或模型凭证。运行前请配置副本的运行环境。'


def fresh_output_directory(site):
    root = Path(getattr(settings, 'WEBSITE_GENERATOR_OUTPUT_ROOT', Path(settings.BASE_DIR) / 'data' / 'generated_sites'))
    return str((root / str(getattr(site, 'pk', site))).resolve())


def _active_user(user):
    return bool(user and user.is_authenticated and get_user_model().objects.filter(pk=user.pk, is_active=True).exists())


def team_role(user, tenant):
    if not _active_user(user) or tenant.status not in ACTIVE_TEAM_STATUSES:
        return None
    if user.is_superuser or tenant.owner_id == user.pk:
        return 'owner'
    return TenantMembership.objects.filter(tenant=tenant, user=user, is_active=True).values_list('role', flat=True).first()


def can_manage_site(user, site):
    if not _active_user(user):
        return False
    if site.tenant_id:
        role = team_role(user, site.tenant)
        return role in ('owner', 'admin') or role == 'member' and site.created_by_id == user.pk
    return user.is_superuser or site.created_by_id == user.pk


def authorize_training_job(user, job):
    if not _active_user(user):
        raise PermissionDenied('训练权重不可访问。')
    if job.tenant_id:
        role = team_role(user, job.tenant)
        allowed = role in ('owner', 'admin') or job.created_by_id == user.pk and role == 'member'
    else:
        allowed = user.is_superuser or job.created_by_id == user.pk
    if not allowed:
        raise PermissionDenied('训练权重不属于当前用户或可管理的团队。')
    return job


def trusted_site_source(user_id, context, training_run_id='', *, node_types=('website_generator',)):
    """Metadata is accepted only when it matches a live engine-owned node execution."""
    from workflows.models import WorkflowExecution, NodeExecution
    allowed_node_types = {'website_generator', 'clip_retrieval', 'clip_classification'}
    if not isinstance(node_types, (tuple, list)) or not node_types or not set(node_types) <= allowed_node_types:
        raise ValueError('Invalid internal generation node types.')
    execution_context = context.get('_execution')
    metadata = execution_context.get('metadata') if isinstance(execution_context, dict) else None
    if not isinstance(metadata, dict):
        metadata = context.get('metadata') if isinstance(context.get('metadata'), dict) else {}
    try:
        identifiers = {key: UUID(str(metadata.get(key, ''))) for key in ('execution_id', 'workflow_id', 'node_id')}
    except (ValueError, TypeError):
        raise PermissionDenied('站点来源必须是当前正在执行的授权工作流节点。')
    execution = WorkflowExecution.objects.select_related('workflow__owner', 'workflow__tenant', 'triggered_by').filter(
        pk=identifiers['execution_id'], workflow_id=identifiers['workflow_id'], status='running').first()
    actor = execution.triggered_by if execution else None
    if execution and actor is None and execution.trigger_type == 'scheduled' and user_id is None:
        actor = execution.workflow.owner
    if not execution or not actor or not _active_user(actor) or user_id is not None and actor.pk != user_id:
        raise PermissionDenied('站点来源必须是当前正在执行的授权工作流节点。')
    workflow = execution.workflow
    if workflow.is_deleted or execution.tenant_id not in (None, workflow.tenant_id):
        raise PermissionDenied('工作流与执行记录的空间不一致。')
    if workflow.tenant_id and team_role(actor, workflow.tenant) not in ('owner', 'admin', 'member'):
        raise PermissionDenied('工作流所属团队的执行权限已失效。')
    if not workflow.tenant_id and actor.pk != workflow.owner_id and not actor.is_superuser:
        raise PermissionDenied('个人工作流不能为其他用户声明站点来源。')
    node_execution = NodeExecution.objects.select_related('node').filter(execution=execution, node_id=identifiers['node_id'],
        node__workflow=workflow, node__node_type__in=node_types, status='running').first()
    if not node_execution:
        raise PermissionDenied('站点来源必须是当前正在执行的授权工作流节点。')
    if training_run_id:
        from training.models import TrainingJob
        try:
            job = TrainingJob.objects.get(pk=UUID(str(training_run_id)))
        except (TrainingJob.DoesNotExist, ValueError):
            raise ValidationError('原训练记录不可用，请明确配置可访问的模型权重。')
        authorize_training_job(actor, job)
        if job.tenant_id != workflow.tenant_id:
            raise PermissionDenied('训练权重与站点工作流必须属于同一空间。')
    return {'created_by': actor, 'tenant': workflow.tenant, 'source_workflow': workflow,
            'source_execution': execution, 'source_node': node_execution.node, 'source_recorded': True}


def source_information(site, user):
    from tenants.access import can_edit_workflow, get_accessible_workflow_queryset
    if not site.source_workflow_id:
        if site.source_recorded:
            return {'status': 'unavailable', 'message': '已记录的源工作流现已删除。可以基于项目配置创建新副本。'}
        return {'status': 'not_recorded', 'message': '此历史项目未记录源工作流；可以基于已保存的项目配置创建副本。'}
    workflow = get_accessible_workflow_queryset(user).filter(pk=site.source_workflow_id).first() if _active_user(user) else None
    if workflow is None:
        return {'status': 'unavailable', 'message': '源工作流已删除或当前无权访问。可由项目所有者或团队管理员创建副本。'}
    return {'status': 'available', 'workflow_id': str(workflow.pk), 'can_edit': can_edit_workflow(user, workflow),
            'node_id': str(site.source_node_id) if site.source_node_id else None,
            'execution_id': str(site.source_execution_id) if site.source_execution_id else None}


def _public_fields(value, keys):
    value = value if isinstance(value, dict) else {}
    def scrub(item):
        if isinstance(item, list):
            return [scrub(child) for child in item]
        if isinstance(item, dict):
            return {key: scrub(child) for key, child in item.items()
                if key.replace('_', '').replace('-', '').lower() not in ('outputdir', 'storagepath', 'mysqlhost', 'mysqlport', 'mysqluser', 'mysqldatabase', 'databaseurl', 'dbhost', 'dbuser', 'dbport', 'dbname')
                and not any(secret in key.replace('_', '').replace('-', '').lower()
                    for secret in ('password', 'secret', 'apikey', 'authorization', 'credential', 'accesstoken', 'refreshtoken', 'connectionstring'))}
        return copy.deepcopy(item)
    return scrub({key: value[key] for key in keys if key in value})


def rebuild_configuration(site, user):
    from training.models import TrainingJob
    manifest = _public_fields(site.model_artifact_manifest, MANIFEST_KEYS)
    training_id = site.training_run_id or manifest.get('trainingJobId') or ''
    if training_id:
        try:
            job = TrainingJob.objects.filter(pk=UUID(str(training_id))).first()
        except (ValueError, TypeError):
            job = None
        if job:
            authorize_training_job(user, job)
            if job.tenant_id != site.tenant_id:
                raise PermissionDenied('训练权重与站点必须属于同一空间。')
        else:
            training_id = ''
            manifest.pop('trainingJobId', None)
    brief = _public_fields(site.site_brief, tuple(site.site_brief)) if isinstance(site.site_brief, dict) else {}
    profile = brief.get('profile') if isinstance(brief.get('profile'), dict) else {}
    wizard = brief.get('wizard') if isinstance(brief.get('wizard'), dict) else {}
    wizard.update(siteName=site.name, usageDescription=site.description or wizard.get('usageDescription', ''), outputDir='', dbEngine='mysql')
    model_path = site.best_weight_path or site.model_path or manifest.get('bestWeightPath') or manifest.get('modelPath') or ''
    artifacts = manifest.get('exportedArtifacts') if isinstance(manifest.get('exportedArtifacts'), dict) else {}
    index_dir = wizard.get('indexDir') or profile.get('index_dir') or manifest.get('indexDir') or artifacts.get('index_dir') or ''
    if not model_path and not training_id and not index_dir:
        raise ValidationError('此项目未保存可重建的模型权重或检索索引，请先补齐项目配置。')
    return {'sourceSiteId': str(site.pk), 'websiteType': site.website_type, 'siteName': site.name, 'description': site.description,
        'modelPath': model_path, 'trainingRunId': training_id, 'modelArtifactManifest': manifest, 'framework': site.framework,
        'labels': copy.deepcopy(site.class_names or site.labels), 'profile': profile, 'wizard': wizard,
        'siteBrief': {**brief, 'profile': profile, 'wizard': wizard}, 'requiredFeatures': copy.deepcopy(site.required_features),
        'themeProfile': _public_fields(site.theme_profile, tuple(site.theme_profile)) if isinstance(site.theme_profile, dict) else {},
        'environmentConfig': {'dbEngine': 'mysql'}, 'agentMemoryEnabled': site.agent_memory_enabled,
        'outputDir': '', 'indexDir': index_dir, 'port': site.port, 'waitForCompletion': True}


@transaction.atomic
def rebuild_site_workflow(site, user, token):
    from workflows.models import Workflow, Node, Edge
    site = GeneratedSite.objects.select_for_update().select_related('tenant').get(pk=site.pk)
    if not can_manage_site(user, site):
        raise PermissionDenied('仅项目所有者或团队管理员可以创建工作流副本。')
    operation, created = SiteWorkflowRebuild.objects.get_or_create(site=site, user=user,
        key_hash=hashlib.sha256(token.encode()).hexdigest())
    if not created:
        if not operation.workflow_id or not Workflow.objects.filter(pk=operation.workflow_id, is_deleted=False).exists():
            raise ValidationError('上次创建的工作流已删除，请刷新项目后重新创建副本。')
        return operation.workflow, False
    config = rebuild_configuration(site, user)
    workflow = Workflow.objects.create(owner=user, tenant=site.tenant, name=f'{site.name} · 副本'[:200],
        description=site.description, status='draft', config={'source_site_id': str(site.pk), 'rebuild_notice': COPY_NOTICE})
    previous = None
    for index, (kind, name, node_config) in enumerate((('start', '开始', {}), ('website_generator', '从项目配置生成站点', config), ('output', '站点结果', {'format': 'json'}), ('end', '结束', {}))):
        node = Node.objects.create(workflow=workflow, node_type=kind, name=name, config=node_config, position_x=100 + index * 280, position_y=160, sort_order=index)
        if previous:
            Edge.objects.create(workflow=workflow, source_node=previous, target_node=node)
        previous = node
    operation.workflow = workflow
    operation.save(update_fields=['workflow'])
    return workflow, True
