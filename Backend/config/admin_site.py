"""
自定义 Django Admin Site
Beautiful Admin Site with Dynamic Feature Management
"""

import json
import logging
import platform
import sys
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db import models
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDay, TruncHour
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from admin.constants import FLOWLY_ADMIN_TABS, PLATFORM_ADMIN_PANEL_TITLE, get_time_greeting
from agents.models import Agent
from tenants.models import Tenant
from users.models import User
from workflows.models import Node, Workflow, WorkflowExecution

try:
    from features.services.feature_service import get_feature_service
except ImportError:
    get_feature_service = None

logger = logging.getLogger(__name__)


class FlowlyAdminSite(AdminSite):
    """
    Flowly 自定义 Admin Site
    提供美化的仪表盘、AI 模型切换、功能管理等
    """

    site_header = format_html(
        '<span style="font-weight:800;font-size:1.3rem;color:#0f2847;">'
        '<span style="color:#2563eb;">Flowly</span>'
        '</span>'
    )
    site_title = PLATFORM_ADMIN_PANEL_TITLE
    index_title = "管理控制台"
    site_url = "/"
    login_template = "admin/login.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registry.update(admin.site._registry)
        self.name = "flowly_admin"

    def index(self, request, extra_context=None):
        """Admin 首页显示欢迎页。"""
        return self.flowly_welcome(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("flowly/welcome/", self.admin_view(self.flowly_welcome), name="flowly_welcome"),
            path("flowly/", self.admin_view(self.flowly_dashboard), name="flowly_dashboard"),
            path("flowly/dashboard-data/", self.admin_view(self.dashboard_data), name="dashboard_data"),
            path("flowly/system-data/", self.admin_view(self.system_data), name="system_data"),
            path("flowly/ai-models-data/", self.admin_view(self.ai_models_data), name="ai_models_data"),
            path("flowly/settings/", self.admin_view(self.settings_hub), name="settings_hub"),
            path("flowly/features/", self.admin_view(self.features_panel), name="features_panel"),
            path("flowly/ai-models/", self.admin_view(self.ai_models_panel), name="ai_models_panel"),
            path("flowly/audit/", self.admin_view(self.audit_panel), name="audit_panel"),
            path("flowly/system/", self.admin_view(self.system_panel), name="system_panel"),
            path("flowly/api/toggle-feature/", self.admin_view(self.toggle_feature_api), name="toggle_feature_api"),
            path("flowly/api/update-config/", self.admin_view(self.update_config_api), name="update_config_api"),
            path("flowly/export/", self.admin_view(self.export_config), name="export_config"),
            path("flowly/import/", self.admin_view(self.import_config), name="import_config"),
        ]
        return custom_urls + urls

    def flowly_welcome(self, request, extra_context=None):
        """管理端欢迎页。"""
        user = request.user
        now = timezone.now()
        greeting = get_time_greeting(now)

        exec_today = WorkflowExecution.objects.filter(
            queued_at__date=now.date()
        ).count()

        context = self.each_context(request)
        context.update({
            "title": "欢迎",
            "page_type": "welcome",
            "greeting": greeting,
            "display_name": user.get_full_name() or user.get_username(),
            "username": user.get_username(),
            "is_superuser": user.is_superuser,
            "last_login": user.last_login,
            "workflows_count": Workflow.objects.count(),
            "executions_today": exec_today,
            "users_count": User.objects.count(),
            "agents_count": Agent.objects.filter(is_active=True).count(),
            "tenants_count": Tenant.objects.count(),
        })
        if extra_context:
            context.update(extra_context)
        return TemplateResponse(request, "admin/flowly_welcome.html", context)

    def flowly_dashboard(self, request, extra_context=None):
        context = self.each_context(request)
        context.update({
            "title": "管理控制台",
            "page_type": "dashboard",
        })
        if extra_context:
            context.update(extra_context)
        return TemplateResponse(request, "admin/flowly_dashboard.html", context)

    def settings_hub(self, request, extra_context=None):
        context = self.each_context(request)
        context.update({"title": "平台配置中心", "page_type": "settings"})
        if extra_context:
            context.update(extra_context)
        return TemplateResponse(request, "admin/flowly_settings_hub.html", context)

    def dashboard_data(self, request):
        """仪表盘数据 API（JSON）。"""
        period = request.GET.get("period", "7d")
        now = timezone.now()

        if period == "24h":
            since = now - timedelta(hours=24)
            trunc = TruncHour
        elif period == "30d":
            since = now - timedelta(days=30)
            trunc = TruncDay
        else:
            since = now - timedelta(days=7)
            trunc = TruncDay

        workflows_total = Workflow.objects.count()
        workflows_active = Workflow.objects.filter(status="active").count()
        workflows_draft = Workflow.objects.filter(status="draft").count()

        exec_qs = WorkflowExecution.objects.filter(queued_at__gte=since)
        executions_total = exec_qs.count()
        executions_success = exec_qs.filter(status="completed").count()
        executions_failed = exec_qs.filter(status="failed").count()

        exec_trend = list(
            exec_qs.annotate(period=trunc("queued_at"))
            .values("period")
            .annotate(
                count=Count("id"),
                success=Count("id", filter=Q(status="completed")),
                failed=Count("id", filter=Q(status="failed")),
            )
            .order_by("period")
        )

        status_qs = WorkflowExecution.objects.all()
        execution_status = {
            "completed": status_qs.filter(status="completed").count(),
            "running": status_qs.filter(status="running").count(),
            "failed": status_qs.filter(status="failed").count(),
            "pending": status_qs.filter(status__in=["pending", "queued"]).count(),
        }

        avg_duration = exec_qs.filter(
            status="completed",
            duration_ms__isnull=False,
        ).aggregate(avg=Avg("duration_ms"))["avg"] or 0

        recent = WorkflowExecution.objects.select_related(
            "workflow", "triggered_by"
        ).order_by("-queued_at")[:20]

        recent_activity = [{
            "id": str(e.id),
            "workflow_name": e.workflow.name if e.workflow else "未知工作流",
            "status": e.status,
            "trigger_type": e.trigger_type or "manual",
            "triggered_by": e.triggered_by.username if e.triggered_by else "",
            "created_at": e.queued_at.isoformat() if e.queued_at else None,
        } for e in recent]

        return JsonResponse({
            "summary": {
                "workflows_total": workflows_total,
                "workflows_active": workflows_active,
                "workflows_draft": workflows_draft,
                "executions_total": executions_total,
                "executions_success": executions_success,
                "executions_failed": executions_failed,
                "success_rate": round(executions_success / executions_total * 100, 1) if executions_total else 0,
                "avg_duration_ms": round(float(avg_duration), 2),
                "users_total": User.objects.count(),
                "tenants_total": Tenant.objects.count(),
                "agents_total": Agent.objects.filter(is_active=True).count(),
                "nodes_total": Node.objects.count(),
            },
            "execution_trend": [{
                "date": item["period"].isoformat() if item["period"] else None,
                "count": item["count"],
                "success": item["success"],
                "failed": item["failed"],
            } for item in exec_trend],
            "execution_status": execution_status,
            "recent_activity": recent_activity,
            "period": period,
        })

    def system_data(self, request):
        """系统状态 API（健康检查 + 资源占用）。"""
        health = {
            "database": self._check_database(),
            "redis": self._check_redis(),
            "storage": self._check_storage(),
            "memory": self._check_memory(),
            "celery": self._check_celery(),
        }

        cpu_percent = None
        mem_percent = None
        mem_used_gb = None
        mem_total_gb = None
        cpu_cores = None

        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.3)
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            mem_used_gb = round(mem.used / (1024 ** 3), 1)
            mem_total_gb = round(mem.total / (1024 ** 3), 1)
            cpu_cores = psutil.cpu_count(logical=True)
        except Exception:
            pass

        healthy_count = sum(
            1 for item in health.values()
            if item.get("status") == "healthy"
        )

        return JsonResponse({
            "health": health,
            "healthy_count": healthy_count,
            "total_checks": len(health),
            "cpu_percent": cpu_percent,
            "mem_percent": mem_percent,
            "mem_used_gb": mem_used_gb,
            "mem_total_gb": mem_total_gb,
            "cpu_cores": cpu_cores,
            "django_version": platform.python_version() and __import__('django').get_version(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "debug_mode": settings.DEBUG,
            "app_version": "2.0.0",
        })

    def ai_models_data(self, request):
        """AI 模型与提供商数据 API。"""
        from gateway.models import AIModel, ModelProvider

        providers = [{
            "id": str(p.id),
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "is_active": p.is_active,
            "model_count": p.models.filter(is_active=True).count(),
        } for p in ModelProvider.objects.prefetch_related("models").order_by("name")]

        models = [{
            "id": str(m.id),
            "name": m.name,
            "model_id": m.model_id,
            "provider": m.provider.name,
            "provider_slug": m.provider.slug,
            "model_type": m.model_type,
            "context_window": m.context_window,
            "input_price": float(m.input_price),
            "output_price": float(m.output_price),
            "is_active": m.is_active,
            "is_default": m.is_default,
            "supports_streaming": m.supports_streaming,
            "description": m.description,
        } for m in AIModel.objects.select_related("provider").order_by("provider__name", "name")]

        env_config = {
            "openai_configured": bool(getattr(settings, "OPENAI_API_KEY", "")),
            "anthropic_configured": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
            "ollama_base_url": getattr(settings, "OLLAMA_BASE_URL", ""),
            "ollama_model": getattr(settings, "OLLAMA_MODEL", ""),
            "nl_workflow_model": getattr(settings, "NL_WORKFLOW_MODEL", ""),
            "nl_workflow_temperature": getattr(settings, "NL_WORKFLOW_TEMPERATURE", 0.7),
        }

        return JsonResponse({
            "providers": providers,
            "models": models,
            "env_config": env_config,
        })

    def features_panel(self, request):
        context = self.each_context(request)
        context.update({"title": "动态功能管理", "page_type": "features"})
        return TemplateResponse(request, "admin/features_panel.html", context)

    def ai_models_panel(self, request):
        context = self.each_context(request)
        context.update({
            "title": "AI 模型配置",
            "page_type": "ai_models",
            "current_ai_config": {
                "openai_api_key": "****" + settings.OPENAI_API_KEY[-4:] if getattr(settings, "OPENAI_API_KEY", "") else "",
                "openai_base_url": getattr(settings, "OPENAI_BASE_URL", ""),
                "anthropic_api_key": "****" + settings.ANTHROPIC_API_KEY[-4:] if getattr(settings, "ANTHROPIC_API_KEY", "") else "",
                "ollama_base_url": getattr(settings, "OLLAMA_BASE_URL", ""),
                "ollama_model": getattr(settings, "OLLAMA_MODEL", ""),
                "nl_workflow_model": getattr(settings, "NL_WORKFLOW_MODEL", ""),
                "nl_workflow_temperature": getattr(settings, "NL_WORKFLOW_TEMPERATURE", 0.7),
            },
        })
        return TemplateResponse(request, "admin/ai_models_panel.html", context)

    def audit_panel(self, request):
        context = self.each_context(request)
        context.update({"title": "审计日志", "page_type": "audit"})
        return TemplateResponse(request, "admin/audit_panel.html", context)

    def system_panel(self, request):
        context = self.each_context(request)
        context.update({
            "title": "系统状态",
            "page_type": "system",
            "django_version": __import__('django').get_version(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
            "debug_mode": settings.DEBUG,
        })
        return TemplateResponse(request, "admin/system_panel.html", context)

    def toggle_feature_api(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "仅支持 POST"}, status=405)

        feature_key = request.POST.get("key")
        if not feature_key:
            return JsonResponse({"error": "key 是必填参数"}, status=400)

        if get_feature_service is None:
            return JsonResponse({"error": "features 模块未安装"}, status=500)

        try:
            feature = get_feature_service().toggle(
                feature_key,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return JsonResponse({
                "success": True,
                "key": feature_key,
                "value": feature.get_value(),
                "new_value": feature.get_value(),
                "display_value": feature.get_display_value(),
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def update_config_api(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "仅支持 POST"}, status=405)

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST

        if get_feature_service is None:
            return JsonResponse({"error": "features 模块未安装"}, status=500)

        # 支持批量 updates 或单条 key/value
        updates = data.get("updates")
        if updates and isinstance(updates, dict):
            results = {}
            for key, value in updates.items():
                feature = get_feature_service().set(
                    key, value,
                    user=request.user if request.user.is_authenticated else None,
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
                results[key] = feature.get_value()
            return JsonResponse({"success": True, "results": results})

        feature_key = data.get("key")
        new_value = data.get("value")
        if not feature_key:
            return JsonResponse({"error": "key 是必填参数"}, status=400)

        try:
            feature = get_feature_service().set(
                feature_key,
                new_value,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return JsonResponse({
                "success": True,
                "key": feature_key,
                "value": feature.get_value(),
                "new_value": feature.get_value(),
                "display_value": feature.get_display_value(),
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def export_config(self, request):
        if get_feature_service is None:
            return JsonResponse({"error": "features 模块未安装"}, status=500)
        config = get_feature_service().export_config()
        response = HttpResponse(config, content_type="application/json")
        response["Content-Disposition"] = "attachment; filename=flowly_config.json"
        return response

    def import_config(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "仅支持 POST"}, status=405)
        if get_feature_service is None:
            return JsonResponse({"error": "features 模块未安装"}, status=500)

        try:
            config = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "无效的 JSON 格式"}, status=400)

        results = get_feature_service().import_config(
            config,
            strategy="merge",
            user=request.user if request.user.is_authenticated else None,
        )
        return JsonResponse(results)

    def _check_database(self):
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
            label = "MySQL" if "mysql" in engine else "PostgreSQL" if "postgres" in engine else "Database"
            return {"status": "healthy", "message": f"{label} 连接正常"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_redis(self):
        try:
            from django.core.cache import cache
            cache.set("health_check", "ok", 10)
            if cache.get("health_check") == "ok":
                return {"status": "healthy", "message": "Redis 连接正常"}
            return {"status": "warning", "message": "Redis 写入失败"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_celery(self):
        try:
            from celery import current_app
            inspect = current_app.control.inspect(timeout=2)
            stats = inspect.stats()
            if stats:
                return {"status": "healthy", "message": f"Celery 运行中 ({len(stats)} worker)"}
            return {"status": "warning", "message": "Celery 未检测到 worker"}
        except Exception as e:
            return {"status": "warning", "message": str(e)}

    def _check_storage(self):
        import os
        try:
            media_root = str(settings.MEDIA_ROOT)
            if os.path.isdir(media_root):
                return {"status": "healthy", "message": "媒体文件目录可用"}
            return {"status": "warning", "message": "媒体文件目录不存在"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_memory(self):
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "status": "healthy" if mem.percent < 85 else "warning",
                "message": f"使用 {mem.percent:.1f}% ({mem.used // 1024 // 1024 // 1024:.1f}GB / {mem.total // 1024 // 1024 // 1024:.1f}GB)",
            }
        except Exception:
            return {"status": "unknown", "message": "无法获取内存信息（需安装 psutil）"}

    def _resolve_flowly_active_tab(self, request):
        """根据当前路径解析 Flowly 面板 Tab 高亮 id。"""
        path = request.path.rstrip('/') or '/'
        if path in ('/admin', '/admin/flowly/welcome'):
            return 'welcome'
        if path == '/admin/flowly':
            return 'dashboard'
        prefix_map = (
            ('/admin/flowly/settings', 'settings'),
            ('/admin/flowly/features', 'features'),
            ('/admin/flowly/ai-models', 'ai_models'),
            ('/admin/flowly/audit', 'audit'),
            ('/admin/flowly/system', 'system'),
        )
        for prefix, tab_id in prefix_map:
            if path.startswith(prefix):
                return tab_id
        return None

    def each_context(self, request):
        ctx = super().each_context(request)
        ctx["flowly_version"] = "2.0.0"
        ctx["flowly_build"] = datetime.now().strftime("%Y%m%d")
        active_tab = self._resolve_flowly_active_tab(request)
        if active_tab is not None:
            ctx["flowly_tabs"] = FLOWLY_ADMIN_TABS
            ctx["flowly_active_tab"] = active_tab
            ctx["flowly_body_class"] = "flowly-panel-page"
        return ctx


flowly_admin_site = FlowlyAdminSite(name="flowly_admin")
admin.site = flowly_admin_site
