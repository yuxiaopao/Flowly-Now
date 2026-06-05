"""
Admin configuration for annotations app.
"""

from django.contrib import admin
from .models import AnnotationProject, AnnotationItem


@admin.register(AnnotationProject)
class AnnotationProjectAdmin(admin.ModelAdmin):
    """Admin for AnnotationProject."""

    list_display = [
        'name', 'annotation_type', 'dataset', 'status',
        'total_items', 'annotated_items', 'model_assisted',
        'created_by', 'created_at'
    ]
    list_filter = ['annotation_type', 'status', 'model_assisted', 'created_at']
    search_fields = ['name', 'dataset__name']
    readonly_fields = ['id', 'total_items', 'annotated_items', 'created_at', 'updated_at']
    raw_id_fields = ['dataset', 'created_by', 'tenant']


@admin.register(AnnotationItem)
class AnnotationItemAdmin(admin.ModelAdmin):
    """Admin for AnnotationItem."""

    list_display = [
        'data_id', 'project', 'pre_label', 'label',
        'status', 'annotated_by', 'annotated_at'
    ]
    list_filter = ['status', 'project', 'created_at']
    search_fields = ['data_id', 'label', 'pre_label']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['project', 'annotated_by']
