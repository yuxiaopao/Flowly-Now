"""
Admin configuration for templates app.
"""

from django.contrib import admin
from .models import TemplateCategory, WorkflowTemplate, TemplateVersion, TemplateUsage, TemplateReview, TemplateFavorite


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'created_by', 'status', 'use_count', 'rating', 'created_at')
    list_filter = ('category', 'status', 'access')
    search_fields = ('name', 'description')
    readonly_fields = ('use_count', 'rating', 'created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'slug', 'description', 'category', 'created_by')
        }),
        ('模板内容', {
            'fields': ('template_data', 'nodes', 'edges')
        }),
        ('变量', {
            'fields': ('variables',)
        }),
        ('分类标签', {
            'fields': ('tags',)
        }),
        ('预览', {
            'fields': ('thumbnail', 'preview_images')
        }),
        ('配置', {
            'fields': ('status', 'access', 'source_workflow', 'config')
        }),
        ('统计', {
            'fields': ('view_count', 'use_count', 'like_count', 'rating', 'rating_count')
        }),
        ('认证', {
            'fields': ('is_verified', 'verified_at')
        }),
        ('时间', {
            'fields': ('published_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TemplateVersion)
class TemplateVersionAdmin(admin.ModelAdmin):
    list_display = ('template', 'version', 'name', 'created_by', 'created_at')
    search_fields = ('template__name', 'version', 'name')
    readonly_fields = ('created_at',)
    list_filter = ('created_at',)

    def has_add_permission(self, request):
        return False


@admin.register(TemplateUsage)
class TemplateUsageAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'workflow', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('template__name', 'user__username')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False


@admin.register(TemplateReview)
class TemplateReviewAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'rating', 'is_verified', 'helpful_count', 'created_at')
    list_filter = ('rating', 'is_verified')
    search_fields = ('template__name', 'user__username', 'title', 'content')
    readonly_fields = ('created_at', 'updated_at')

    actions = ['approve_reviews']

    @admin.action(description='标记为已验证购买')
    def approve_reviews(self, request, queryset):
        queryset.update(is_verified=True)


@admin.register(TemplateFavorite)
class TemplateFavoriteAdmin(admin.ModelAdmin):
    list_display = ('template', 'user', 'created_at')
    search_fields = ('template__name', 'user__username')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        return False
