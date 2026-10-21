"""
URL configuration for Flowly project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.generators import SchemaGenerator
from rest_framework.response import Response
import logging
import traceback

logger = logging.getLogger('django')


class RobustSchemaGenerator(SchemaGenerator):
    """Schema generator that logs errors instead of crashing."""

    def get_schema(self, request=None, public=False):
        try:
            return super().get_schema(request=request, public=public)
        except (AssertionError, OSError) as e:
            logger.error(f"[drf-spectacular] Schema generation failed: {e}")
            logger.error(traceback.format_exc())
            return {'openapi': '3.0.0', 'info': {'title': 'Flowly API', 'version': '1.0'}, 'paths': {}}


class RobustSpectacularAPIView(SpectacularAPIView):
    generator_class = RobustSchemaGenerator

    def _get_schema_response(self, request):
        version = self.api_version or request.version or self._get_version_parameter(request)
        generator = self.generator_class(urlconf=self.urlconf, api_version=version, patterns=self.patterns)
        schema = generator.get_schema(request=request, public=self.serve_public)
        return Response(
            data=schema,
            headers={"Content-Disposition": f'inline; filename="{self._get_filename(request, version)}"'}
        )
from config.handlers import handler400, handler403, handler404, handler500
from config.admin_site import flowly_admin_site
from admin.module_views import PublicSiteConfigView
from admin.auth_assistant import PublicAuthAssistantChatView

# Custom error handlers
handler400 = 'config.handlers.handler400'
handler403 = 'config.handlers.handler403'
handler404 = 'config.handlers.handler404'
handler500 = 'config.handlers.handler500'

urlpatterns = [
    # 自定义美化 Admin（替换默认 Django Admin）
    path('admin/', flowly_admin_site.urls),
    # Core app: health, notifications, audit
    path('api/', include('core.urls')),
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/', include('core.urls')),
    path('api/v1/', include('workflows.urls')),
    path('api/v1/datasets/', include('datasets.urls')),
    path('api/v1/agents/', include('agents.urls')),
    path('api/v1/nl-workflow/', include('nl_to_workflow.urls')),
    path('api/v1/prompts/', include('prompts.urls')),
    path('api/v1/tenants/', include('tenants.urls')),
    path('api/v1/monitoring/', include('monitoring.urls')),
    path('api/v1/rag/', include('rag.urls')),
    path('api/v1/gateway/', include('gateway.urls')),
    path('api/v1/billing/', include('billing.urls')),
    path('api/v1/integrations/', include('integrations.urls')),
    path('api/v1/branding/', include('branding.urls')),
    path('api/v1/marketplace/', include('marketplace.urls')),
    path('api/v1/templates/', include('templates.urls')),
    path('api/v1/admin/', include('admin.urls')),
    path('api/v1/dataset-recommend/', include('dataset_recommend.urls')),
    path('api/v1/annotations/', include('annotations.urls')),
    path('api/v1/augmentations/', include('augmentation.urls')),
    path('api/v1/training/', include('training.urls')),
    path('api/v1/website-generator/', include('website_generator.urls')),
    path('api/v1/evaluations/', include('evaluation.urls')),
    path('api/v1/features/', include('features.urls')),
    path('api/v1/public/site-config/', PublicSiteConfigView.as_view(), name='public-site-config'),
    path('api/v1/public/auth-assistant/chat/', PublicAuthAssistantChatView.as_view(), name='public-auth-assistant-chat'),
    path('api/v1/codegraph/', include('codegraph.urls')),
    # API Documentation
    path('api/schema/', RobustSpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Serve media + static in development (finders include admin_static/)
if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from core.views.media_views import serve_media

    urlpatterns += static(settings.MEDIA_URL, view=serve_media, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
