"""
URL patterns for agents app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentViewSet, AgentConversationViewSet, AgentToolViewSet, AgentExecutionViewSet

# Sub-routers use empty prefix since they're nested under explicit paths
conversations_router = DefaultRouter()
conversations_router.register(r'', AgentConversationViewSet, basename='conversation')

executions_router = DefaultRouter()
executions_router.register(r'', AgentExecutionViewSet, basename='execution')

tools_router = DefaultRouter()
tools_router.register(r'', AgentToolViewSet, basename='agent-tool')

# Main router for agent CRUD
agent_router = DefaultRouter()
agent_router.register(r'', AgentViewSet, basename='agent')

urlpatterns = [
    # Sub-resource routes - trailing slash matches DRF router defaults
    path('conversations/', include((conversations_router.urls, 'conversations'))),
    path('executions/', include((executions_router.urls, 'executions'))),
    path('tools/', include((tools_router.urls, 'tools'))),
    path('', include(agent_router.urls)),
]
