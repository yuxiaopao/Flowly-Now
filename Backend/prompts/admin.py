"""
Django Admin configuration for prompts app.
"""

from django.contrib import admin
from .models import PromptCategory, PromptTemplate, PromptRating


@admin.register(PromptCategory)
class PromptCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'sort_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'name']


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'prompt_type', 'category', 'model_preferences', 'avg_rating', 'use_count', 'is_active', 'created_at']
    list_filter = ['prompt_type', 'is_active', 'category', 'created_at']
    search_fields = ['name', 'description', 'template']
    raw_id_fields = ['category', 'created_by']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(PromptRating)
class PromptRatingAdmin(admin.ModelAdmin):
    list_display = ['user', 'prompt', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'prompt__name']
    raw_id_fields = ['user', 'prompt']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
