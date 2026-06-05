"""
Django Admin configuration for evaluation app.
"""

from django.contrib import admin
from .models import EvaluationJob


@admin.register(EvaluationJob)
class EvaluationJobAdmin(admin.ModelAdmin):
    list_display = ['name', 'job_id', 'status', 'created_by', 'created_at', 'completed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'job_id', 'model_path']
    raw_id_fields = ['created_by']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
