from django.contrib import admin
from .models import FeatureCategory, SystemFeature, FeatureAuditLog


@admin.register(FeatureCategory)
class FeatureCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'sort_order', 'created_at']
    search_fields = ['name', 'slug']
    ordering = ['sort_order', 'name']


@admin.register(SystemFeature)
class SystemFeatureAdmin(admin.ModelAdmin):
    list_display = ['key', 'category', 'name', 'value_type', 'is_enabled', 'is_readonly', 'updated_at']
    list_filter = ['category', 'value_type', 'is_enabled', 'is_readonly']
    search_fields = ['key', 'name', 'description']
    ordering = ['category__sort_order', 'order', 'key']
    readonly_fields = ['key', 'source_file', 'source_line', 'created_at', 'updated_at']

    fieldsets = (
        ('基本信息', {'fields': ('category', 'key', 'name', 'description')}),
        ('值配置', {'fields': ('value_type', 'value', 'default_value', 'choices',
                               'min_value', 'max_value', 'step', 'placeholder', 'suffix')}),
        ('UI配置', {'fields': ('group', 'order', 'is_enabled', 'is_visible', 'is_readonly')}),
        ('来源', {'fields': ('source_file', 'source_line', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(FeatureAuditLog)
class FeatureAuditLogAdmin(admin.ModelAdmin):
    list_display = ['feature', 'action', 'changed_by', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['feature__key', 'feature__name']
    readonly_fields = ['feature', 'action', 'old_value', 'new_value', 'changed_by', 'ip_address', 'reason', 'created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
