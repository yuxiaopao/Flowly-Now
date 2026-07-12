"""
URL patterns for agents app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AgentViewSet, AgentConversationViewSet, AgentToolViewSet, AgentExecutionViewSet,
    AgentCollaborationViewSet
)
from .views_desktop import DesktopAgentViewSet

# Sub-routers use empty prefix since they're nested under explicit paths
conversations_router = DefaultRouter()
conversations_router.register(r'', AgentConversationViewSet, basename='conversation')

executions_router = DefaultRouter()
executions_router.register(r'', AgentExecutionViewSet, basename='execution')

tools_router = DefaultRouter()
tools_router.register(r'', AgentToolViewSet, basename='agent-tool')

collaborations_router = DefaultRouter()
collaborations_router.register(r'', AgentCollaborationViewSet, basename='collaboration')

# Main router for agent CRUD
agent_router = DefaultRouter()
agent_router.register(r'', AgentViewSet, basename='agent')

# Desktop agent router
desktop_agent_router = DefaultRouter()
desktop_agent_router.register(r'', DesktopAgentViewSet, basename='desktop-agent')

urlpatterns = [
    # Sub-resource routes - trailing slash matches DRF router defaults
    path('conversations/', include((conversations_router.urls, 'conversations'))),
    path('executions/', include((executions_router.urls, 'executions'))),
    path('tools/', include((tools_router.urls, 'tools'))),
    path('collaborations/', include((collaborations_router.urls, 'collaborations'))),
    # Desktop agents
    path('desktop/', include((desktop_agent_router.urls, 'desktop'))),
    # Main agent routes
    path('', include(agent_router.urls)),
]
