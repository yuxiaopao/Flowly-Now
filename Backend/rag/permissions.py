"""POST retrieval remains readable; all other object mutations require fresh management rights."""
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .access import active_actor, can_manage_resource

READ_ACTIONS = frozenset(('search', 'ask', 'query', 'test_connection'))


class RAGResourcePermission(BasePermission):
    def has_permission(self, request, view):
        return active_actor(request.user) is not None

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or getattr(view, 'action', None) in READ_ACTIONS:
            return True
        return can_manage_resource(request.user, obj)
