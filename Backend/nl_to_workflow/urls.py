"""
URL patterns for NL to Workflow app.
"""

from django.urls import path
from .views import (
    NLModelListView,
    NLSessionViewSet, NLSessionDetailView,
    NLSessionMessageView, NLSessionMessageStreamView,
    NLSessionConfirmView,
    NLWorkflowPreviewView,
    NLWorkflowStreamView,
    NLWorkflowAnalyzeIntentView,
    NLWorkflowSuggestView,
)

urlpatterns = [
    path('models/', NLModelListView.as_view(), name='nl-models'),
    path('sessions/', NLSessionViewSet.as_view(), name='nl-sessions'),
    path('sessions/<uuid:session_id>/', NLSessionDetailView.as_view(), name='nl-session-detail'),
    path('sessions/<uuid:session_id>/message/', NLSessionMessageView.as_view(), name='nl-session-message'),
    path('sessions/<uuid:session_id>/message/stream/', NLSessionMessageStreamView.as_view(), name='nl-session-message-stream'),
    path('sessions/<uuid:session_id>/confirm/', NLSessionConfirmView.as_view(), name='nl-session-confirm'),
    path('preview/', NLWorkflowPreviewView.as_view(), name='nl-workflow-preview'),
    path('stream/', NLWorkflowStreamView.as_view(), name='nl-workflow-stream'),
    path('analyze-intent/', NLWorkflowAnalyzeIntentView.as_view(), name='nl-workflow-analyze-intent'),
    path('suggest/', NLWorkflowSuggestView.as_view(), name='nl-workflow-suggest'),
]
