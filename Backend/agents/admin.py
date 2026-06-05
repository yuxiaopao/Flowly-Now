"""
Admin configuration for agents app.
"""

from django.contrib import admin
from .models import Agent, AgentTool, AgentConversation, AgentExecution


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'agent_type', 'model', 'is_active', 'created_at']
    list_filter = ['agent_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']


@admin.register(AgentConversation)
class AgentConversationAdmin(admin.ModelAdmin):
    list_display = ['agent', 'user', 'message_count', 'token_count', 'updated_at']
    list_filter = ['agent', 'created_at']
