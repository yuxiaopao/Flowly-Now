"""Permissions shared by the public template catalogues."""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class TemplateAccessPermission(BasePermission):
    """Public reads, authenticated interactions, owner-only definition writes."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if view.action in ('update', 'partial_update', 'destroy'):
            return obj.created_by_id == request.user.pk or request.user.is_superuser
        return request.user.is_authenticated


class PublicReadAdminWrite(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or bool(request.user and request.user.is_staff)
