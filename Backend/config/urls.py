"""
URL configuration for Flowly project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from config.handlers import handler400, handler403, handler404, handler500
from config.admin_site import flowly_admin_site

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
    path('api/v1/codegraph/', include('codegraph.urls')),
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if getattr(settings, 'STATIC_URL', None):
        urlpatterns += static(settings.STATIC_URL, document_root=getattr(settings, 'STATIC_ROOT', None))
