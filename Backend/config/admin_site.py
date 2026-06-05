"""
自定义 Django Admin Site
Beautiful Admin Site with Dynamic Feature Management
"""

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models
from django.utils.html import format_html, format_html_join
from django.urls import reverse, path
from django.db.models import Count, Sum, Avg, F
from django.db.models.functions import TruncDay, TruncHour
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from datetime import datetime, timedelta
import json
import logging
import sys

from workflows.models import Workflow, WorkflowExecution, Node, AuditLog
from agents.models import Agent
from users.models import User
from tenants.models import Tenant

try:
    from features.services.feature_service import get_feature_service
except ImportError:
    get_feature_service = None

logger = logging.getLogger(__name__)


class FlowlyAdminSite(AdminSite):
    """
    e-Flowly 自定义 Admin Site
    提供美化的仪表盘、AI 模型切换、功能管理等
    """

    site_header = format_html(
        '<span style="font-weight:800;font-size:1.3rem;">'
        '<span style="color:#6366f1;">e</span>'
        '<span style="color:#818cf8;">-Flowly</span>'
        '</span>'
    )
    site_title = "e-Flowly 管理后台"
    index_title = "管理控制台"
    site_url = "/"

    # 自定义登录页面背景
    login_template = "admin/login.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registry.update(admin.site._registry)
        self.name = "flowly_admin"

    def get_urls(self):
        """
        添加自定义管理后台 URL
        /admin/flowly/            - 动态功能管理面板
        /admin/flowly/dashboard/ - 仪表盘数据
        /admin/flowly/features/   - 功能开关管理
        /admin/flowly/ai-models/  - AI 模型配置
        /admin/flowly/audit/      - 审计日志
        /admin/flowly/system/     - 系统状态
        """
        urls = super().get_urls()
        custom_urls = [
            path("flowly/", self.admin_view(self.flowly_dashboard), name="flowly_dashboard"),
            path("flowly/dashboard-data/", self.admin_view(self.dashboard_data), name="dashboard_data"),
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

    @login_required
    def flowly_dashboard(self, request):
        """
        自定义首页仪表盘 - 替代默认的 App 列表
        """
        context = self.each_context(request)
        context.update({
            "title": "管理控制台",
            "page_type": "dashboard",
        })
        return TemplateResponse(request, "admin/flowly_dashboard.html", context)

    @login_required
    def dashboard_data(self, request):
        """
        仪表盘数据 API（JSON）
        """
        period = request.GET.get("period", "7d")
        now = datetime.now()

        if period == "24h":
            since = now - timedelta(hours=24)
            trunc = TruncHour
        elif period == "30d":
            since = now - timedelta(days=30)
            trunc = TruncDay
        else:
            since = now - timedelta(days=7)
            trunc = TruncDay

        # 工作流统计
        workflows_total = Workflow.objects.count()
        workflows_active = Workflow.objects.filter(status="active").count()
        workflows_draft = Workflow.objects.filter(status="draft").count()

        # 执行统计
        executions_total = WorkflowExecution.objects.filter(
            created_at__gte=since
        ).count()
        executions_success = WorkflowExecution.objects.filter(
            created_at__gte=since, status="completed"
        ).count()
        executions_failed = WorkflowExecution.objects.filter(
            created_at__gte=since, status="failed"
        ).count()

        # 执行时间趋势
        exec_trend = list(
            WorkflowExecution.objects.filter(
                created_at__gte=since
            ).annotate(
                period=trunc("created_at")
            ).values("period").annotate(
                count=Count("id"),
                success=Count("id", filter=models.Q(status="completed")),
                failed=Count("id", filter=models.Q(status="failed"))
            ).order_by("period")
        )

        # 用户 & 租户统计
        users_total = User.objects.count()
        tenants_total = Tenant.objects.count()
        agents_total = Agent.objects.count()

        # 节点统计
        nodes_total = Node.objects.count()

        # 平均执行时间
        avg_duration = WorkflowExecution.objects.filter(
            created_at__gte=since,
            status="completed",
            duration__isnull=False
        ).aggregate(avg=Avg("duration"))["avg"] or 0

        return JsonResponse({
            "summary": {
                "workflows_total": workflows_total,
                "workflows_active": workflows_active,
                "workflows_draft": workflows_draft,
                "executions_total": executions_total,
                "executions_success": executions_success,
                "executions_failed": executions_failed,
                "success_rate": round(executions_success / executions_total * 100, 1) if executions_total else 0,
                "avg_duration_ms": round(avg_duration, 2),
                "users_total": users_total,
                "tenants_total": tenants_total,
                "agents_total": agents_total,
                "nodes_total": nodes_total,
            },
            "execution_trend": [
                {
                    "date": item["period"].isoformat() if item["period"] else None,
                    "count": item["count"],
                    "success": item["success"],
                    "failed": item["failed"],
                }
                for item in exec_trend
            ],
            "period": period,
        })

    @login_required
    def features_panel(self, request):
        """动态功能管理面板"""
        context = self.each_context(request)
        context["title"] = "动态功能管理"
        context["page_type"] = "features"
        return TemplateResponse(request, "admin/features_panel.html", context)

    @login_required
    def ai_models_panel(self, request):
        """AI 模型配置面板"""
        context = self.each_context(request)
        context["title"] = "AI 模型配置"
        context["page_type"] = "ai_models"

        # 读取当前 AI 配置
        context["current_ai_config"] = {
            "openai_api_key": "****" + settings.OPENAI_API_KEY[-4:] if settings.OPENAI_API_KEY else "",
            "openai_base_url": settings.OPENAI_BASE_URL,
            "anthropic_api_key": "****" + settings.ANTHROPIC_API_KEY[-4:] if settings.ANTHROPIC_API_KEY else "",
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "ollama_model": settings.OLLAMA_MODEL,
            "nl_workflow_model": settings.NL_WORKFLOW_MODEL,
            "nl_workflow_temperature": settings.NL_WORKFLOW_TEMPERATURE,
        }

        return TemplateResponse(request, "admin/ai_models_panel.html", context)

    @login_required
    def audit_panel(self, request):
        """审计日志面板"""
        context = self.each_context(request)
        context["title"] = "审计日志"
        context["page_type"] = "audit"

        # 获取最近的操作日志
        from workflows.models import AuditLog
        logs = AuditLog.objects.select_related("user").order_by("-created_at")[:100]

        context["recent_logs"] = logs
        return TemplateResponse(request, "admin/audit_panel.html", context)

    @login_required
    def system_panel(self, request):
        """系统状态面板"""
        context = self.each_context(request)
        context["title"] = "系统状态"
        context["page_type"] = "system"

        # 健康检查
        health = {
            "database": self._check_database(),
            "redis": self._check_redis(),
            "storage": self._check_storage(),
            "memory": self._check_memory(),
        }
        context["health"] = health
        context["django_version"] = settings.VERSION if hasattr(settings, "VERSION") else "5.x"
        context["python_version"] = f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}"
        context["debug_mode"] = settings.DEBUG

        return TemplateResponse(request, "admin/system_panel.html", context)

    @login_required
    def toggle_feature_api(self, request):
        """API: 切换功能开关"""
        if request.method != "POST":
            return JsonResponse({"error": "仅支持 POST"}, status=405)

        feature_key = request.POST.get("key")
        if not feature_key:
            return JsonResponse({"error": "key 是必填参数"}, status=400)

        # 使用 features 服务
        try:
            feature = get_feature_service().toggle(
                feature_key,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
            return JsonResponse({
                "success": True,
                "key": feature_key,
                "new_value": feature.get_value(),
                "display_value": feature.get_display_value(),
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    @login_required
    def update_config_api(self, request):
        """API: 更新配置"""
        if request.method != "POST":
            return JsonResponse({"error": "仅支持 POST"}, status=405)

        import json
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = request.POST

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
                "display_value": feature.get_display_value(),
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    @login_required
    def export_config(self, request):
        """导出配置"""
        if get_feature_service is None:
            return JsonResponse({"error": "features 模块未安装"}, status=500)
        config = get_feature_service().export_config()
        response = HttpResponse(config, content_type="application/json")
        response["Content-Disposition"] = "attachment; filename=flowly_config.json"
        return response

    @login_required
    def import_config(self, request):
        """导入配置"""
        if request.method == "POST":
            import json
            try:
                config = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "无效的 JSON 格式"}, status=400)

            if get_feature_service is None:
                return JsonResponse({"error": "features 模块未安装"}, status=500)
            results = get_feature_service().import_config(
                config,
                strategy="merge",
                user=request.user if request.user.is_authenticated else None,
            )
            return JsonResponse(results)
        return JsonResponse({"error": "仅支持 POST"}, status=405)

    def _check_database(self):
        try:
            from django.db import connection
            with connection.cursor() as c:
                c.execute("SELECT 1")
            return {"status": "healthy", "message": "MySQL 8.0 连接正常"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_redis(self):
        try:
            import django_redis
            from django.core.cache import cache
            cache.set("health_check", "ok", 10)
            val = cache.get("health_check")
            if val == "ok":
                return {"status": "healthy", "message": "Redis 连接正常"}
            return {"status": "warning", "message": "Redis 写入失败"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_storage(self):
        import os
        try:
            static_root = settings.STATIC_ROOT or settings.STATICFILES_DIRS[0]
            if os.path.exists(static_root):
                size = sum(
                    os.path.getsize(os.path.join(dp, f))
                    for dp, dn, fn in os.walk(static_root)
                    for f in fn
                )
                return {"status": "healthy", "message": f"静态文件目录可用 ({size // 1024 // 1024} MB)"}
            return {"status": "warning", "message": "静态文件目录不存在"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _check_memory(self):
        import psutil
        try:
            mem = psutil.virtual_memory()
            return {
                "status": "healthy" if mem.percent < 80 else "warning",
                "message": f"使用 {mem.percent:.1f}% ({mem.used // 1024 // 1024 // 1024:.1f}GB / {mem.total // 1024 // 1024 // 1024:.1f}GB)"
            }
        except Exception:
            return {"status": "unknown", "message": "无法获取内存信息"}

    def each_context(self, request):
        """传递给模板的上下文"""
        ctx = super().each_context(request)
        ctx["flowly_version"] = "2.0.0"
        ctx["flowly_build"] = "20240501"
        return ctx


# 创建自定义 Admin Site 实例
flowly_admin_site = FlowlyAdminSite(name="flowly_admin")

# 将默认 admin.site 替换为自定义站点
admin.site = flowly_admin_site
