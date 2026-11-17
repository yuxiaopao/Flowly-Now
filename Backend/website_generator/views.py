"""
Views for website generator app.
"""

import os
import logging
import zipfile
import io
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import GeneratedSite
from .serializers import (
    GeneratedSiteSerializer, GeneratedSiteCreateSerializer, GeneratedSiteUpdateSerializer
)
from .generators.classification import ClassificationGenerator
from .generators.regression import RegressionGenerator
from .generators.detection import DetectionGenerator
from .generators.nlp import NLPGGenerator

logger = logging.getLogger(__name__)


def register_site_codegraph(site):
    """Register generated site output dir in CodeGraph PROJECT_CONFIGS."""
    from codegraph.views import PROJECT_CONFIGS
    if not site.output_dir or not os.path.isdir(site.output_dir):
        return None
    next_id = max(PROJECT_CONFIGS.keys(), default=0) + 1
    PROJECT_CONFIGS[next_id] = {
        'name': site.name,
        'path': site.output_dir,
        'generated_site_id': str(site.id),
    }
    site.codegraph_project_id = next_id
    site.save(update_fields=['codegraph_project_id'])
    return next_id


class GeneratedSiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for GeneratedSite management.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = GeneratedSite.objects.select_related('tenant', 'source_workflow')
        if not user or not user.is_authenticated or not user.is_active:
            return qs.none()
        if not user.is_superuser:
            from tenants.models import TenantMembership
            from .provenance import ACTIVE_TEAM_STATUSES
            tenant_ids = TenantMembership.objects.filter(user=user, is_active=True, tenant__status__in=ACTIVE_TEAM_STATUSES).values('tenant_id')
            qs = qs.filter(Q(created_by=user, tenant__isnull=True) | Q(tenant_id__in=tenant_ids) |
                Q(tenant__owner=user, tenant__status__in=ACTIVE_TEAM_STATUSES))

        show_in_nav = self.request.query_params.get('show_in_nav')
        if show_in_nav in ('true', '1'):
            qs = qs.filter(show_in_nav=True)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return GeneratedSiteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return GeneratedSiteUpdateSerializer
        return GeneratedSiteSerializer

    def require_manage(self, site):
        from .provenance import can_manage_site
        if not can_manage_site(self.request.user, site):
            raise PermissionDenied('仅项目所有者或团队管理员可以修改此项目。')

    def perform_update(self, serializer):
        self.require_manage(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.require_manage(instance)
        instance.delete()

    @action(detail=True, methods=['post'], url_path='rebuild-workflow')
    def rebuild_workflow(self, request, pk=None):
        from .provenance import rebuild_site_workflow, COPY_NOTICE
        site = self.get_object()
        self.require_manage(site)
        if request.data:
            raise ValidationError('此接口仅从已授权的站点记录读取配置，不接受客户端配置覆盖。')
        token = request.headers.get('Idempotency-Key', '').strip()
        if not token or len(token) > 128:
            raise ValidationError('请提供非空且不超过128字符的 Idempotency-Key，以便安全重试。')
        workflow, created = rebuild_site_workflow(site, request.user, token)
        return Response({'workflow_id': str(workflow.pk), 'source_site_id': str(site.pk), 'created': created,
                         'notice': COPY_NOTICE}, status=201 if created else 200)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Start website generation.
        
        Creates a GeneratedSite record and runs the generator in a background thread.
        """
        serializer = GeneratedSiteCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        site = serializer.save(
            status='profiling',
            created_by=request.user,
        )

        def run_generation():
            try:
                from website_generator.generators import get_generator
                if not site.output_dir:
                    from .provenance import fresh_output_directory
                    site.output_dir = fresh_output_directory(site)
                    site.save(update_fields=['output_dir'])

                site.status = 'environment_ready'
                site.progress = 15
                site.save(update_fields=['status', 'progress'])

                environment_config = dict(site.environment_config or {})
                theme_profile = dict(site.theme_profile or {})
                site_brief = dict(site.site_brief or {})
                wizard = dict(site_brief.get('wizard') or {})
                if theme_profile:
                    wizard.update(theme_profile)
                if site.description and not wizard.get('usageDescription'):
                    wizard['usageDescription'] = site.description
                if site.name and not wizard.get('siteName'):
                    wizard['siteName'] = site.name

                generator = get_generator(site.website_type, {
                    'output_dir': site.output_dir,
                    'model_path': site.model_path,
                    'model_type': site.model_type,
                    'labels': site.labels,
                    'framework': site.framework,
                    'website_type': site.website_type,
                    'frontend_framework': site.frontend_framework,
                    'backend_framework': site.backend_framework,
                    'port': site.port,
                    'name': site.name,
                    'description': site.description,
                    'model_artifact_manifest': site.model_artifact_manifest,
                    'required_features': site.required_features,
                    'site_brief': site_brief,
                    'theme_profile': theme_profile,
                    'environment_config': environment_config,
                    'dbEngine': environment_config.get('dbEngine') or 'mysql',
                    'profile': site_brief.get('profile') or {},
                    'wizard': wizard,
                    'agent_memory_enabled': site.agent_memory_enabled,
                })

                site.status = 'backend_ready'
                site.progress = 35
                site.save(update_fields=['status', 'progress'])
                result = generator.generate()
                if not result.get('success'):
                    raise RuntimeError(result.get('error') or 'Website generator returned an unsuccessful result')

                site.generated_files = result.get('generated_files', [])
                site.status = 'preview_ready'
                site.progress = 90
                site.inference_endpoint = f"http://localhost:{site.port}/predict"
                site.last_preview_url = f"http://localhost:{site.port}/"
                site.preview_status = 'stale'
                site.completed_at = timezone.now()
                site.save()

                try:
                    register_site_codegraph(site)
                except Exception as cg_err:
                    logger.warning(f"CodeGraph registration skipped for site {site.id}: {cg_err}")

                site.status = 'completed'
                site.progress = 100
                site.save(update_fields=['status', 'progress'])

            except Exception as e:
                logger.exception(f"Website generation failed for site {site.id}")
                site.status = 'failed_with_report'
                site.error_message = str(e)
                site.completed_at = timezone.now()
                site.save()

        import threading
        t = threading.Thread(target=run_generation)
        t.start()

        return Response(GeneratedSiteSerializer(site, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download generated website as a ZIP file."""
        site = self.get_object()

        if site.status != 'completed':
            return Response({'error': 'Site not yet generated'}, status=status.HTTP_400_BAD_REQUEST)

        if not os.path.exists(site.output_dir):
            return Response({'error': 'Output directory not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(site.output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, site.output_dir)
                        zipf.write(file_path, arcname)

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{site.name.replace(" ", "_")}.zip"'
            return response

        except Exception as e:
            logger.error(f"Failed to create ZIP for site {pk}: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def deploy(self, request, pk=None):
        """Deploy the generated website locally."""
        site = self.get_object()
        self.require_manage(site)

        if site.status != 'completed':
            return Response({'error': 'Site not yet generated'}, status=status.HTTP_400_BAD_REQUEST)

        import subprocess
        import threading

        def run_deploy():
            try:
                backend_dir = os.path.join(site.output_dir, 'backend')
                if os.path.exists(os.path.join(backend_dir, 'app.py')):
                    subprocess.Popen(
                        ['python', 'app.py'],
                        cwd=backend_dir,
                        env={**os.environ, 'MODEL_PATH': site.model_path}
                    )
            except Exception as e:
                logger.error(f"Deploy failed for site {pk}: {str(e)}")

        t = threading.Thread(target=run_deploy)
        t.start()

        return Response({
            'message': 'Deployment started',
            'endpoint': site.inference_endpoint,
        })

    @action(detail=True, methods=['post'], url_path='agent/message')
    def agent_message(self, request, pk=None):
        """Project Agent: apply user edit request + mandatory QA."""
        site = self.get_object()
        self.require_manage(site)
        content = (request.data.get('content') or request.data.get('message') or '').strip()
        if not content:
            return Response({'error': 'content 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        from .site_factory.project_agent import run_agent_for_site

        result = run_agent_for_site(
            site,
            content,
            qa_profile=request.data.get('qaProfile') or 'default',
            auto_qa=request.data.get('autoQaAfterEdit', True),
            confirm_core_edit=bool(request.data.get('confirmCoreEdit', False)),
            user=request.user,
            agent_mode=request.data.get('agentMode') or 'auto',
        )

        if not result.get('success'):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)
