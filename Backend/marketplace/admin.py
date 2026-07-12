"""
Admin configuration for marketplace app.
"""

from django.contrib import admin
from .models import TemplateCategory, WorkflowTemplate, TemplateInstall, TemplateRating, TemplateComment, TemplateFavorite


MARKETPLACE_TEMPLATE_ADMIN_LIST_FILTERS = (
    'category',
    'is_published',
    'is_featured',
    'is_verified',
)


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'created_by', 'is_published', 'is_featured',
                   'install_count', 'avg_rating', 'created_at')
    list_filter = MARKETPLACE_TEMPLATE_ADMIN_LIST_FILTERS
    search_fields = ('name', 'description', 'tags')
    readonly_fields = ('install_count', 'avg_rating', 'created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description', 'category', 'created_by')
        }),
        ('工作流数据', {
            'fields': ('workflow_data', 'nodes', 'edges')
        }),
        ('标签', {
            'fields': ('tags',)
        }),
        ('预览', {
            'fields': ('preview_image',)
        }),
        ('统计', {
            'fields': ('install_count', 'view_count', 'avg_rating', 'report_count')
        }),
        ('状态', {
            'fields': ('is_published', 'is_featured', 'is_verified')
        }),
        ('时间', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TemplateInstall)
class TemplateInstallAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'workflow', 'installed_at')
    list_filter = ('installed_at',)
    search_fields = ('template__name', 'user__username')
    readonly_fields = ('installed_at',)

    def has_add_permission(self, request):
        return False


@admin.register(TemplateRating)
class TemplateRatingAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('template__name', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(TemplateComment)
class TemplateCommentAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'like_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('template__name', 'user__username', 'content')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TemplateFavorite)
class TemplateFavoriteAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'created_at')
    search_fields = ('template__name', 'user__username')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False
