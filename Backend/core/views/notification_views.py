"""
Notification API views.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from ..models.notification import Notification, NotificationPreference, NotificationType
from ..serializers.notification_serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
)


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for user notifications."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        self.get_queryset().filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'status': 'all marked as read'})

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a notification."""
        notification = self.get_object()
        notification.is_archived = True
        notification.save(update_fields=['is_archived'])
        return Response({'status': 'archived'})

    @action(detail=False, methods=['post'])
    def archive_all(self, request):
        """Archive all read notifications."""
        self.get_queryset().filter(is_read=True).update(is_archived=True)
        return Response({'status': 'all archived'})

    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Delete all notifications."""
        self.get_queryset().delete()
        return Response({'status': 'all cleared'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = self.get_queryset().filter(is_read=False, is_archived=False).count()
        return Response({'count': count})

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent notifications (last 5)."""
        notifications = self.get_queryset().filter(
            is_archived=False
        ).order_by('-created_at')[:5]

        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def delete_read(self, request):
        """Delete all read notifications."""
        deleted_count, _ = self.get_queryset().filter(
            is_read=True,
            is_archived=True
        ).delete()
        return Response({'deleted': deleted_count})


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for notification preferences."""

    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def get_object(self):
        """Get or create preference for current user."""
        prefs, _ = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return prefs

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Get current user's preferences."""
        prefs = self.get_object()
        serializer = self.get_serializer(prefs)
        return Response(serializer.data)

    @action(detail=False, methods=['put'])
    def update_preferences(self, request):
        """Update notification preferences."""
        prefs = self.get_object()

        # Update fields
        for field in [
            'workflow_completed', 'workflow_failed', 'workflow_scheduled',
            'agent_completed', 'agent_failed', 'trigger_activated',
            'alert_triggered', 'system_message', 'user_invitation',
            'comment', 'mention', 'email_enabled', 'push_enabled',
            'in_app_enabled', 'quiet_hours_enabled'
        ]:
            if field in request.data:
                setattr(prefs, field, request.data[field])

        if 'quiet_hours_start' in request.data:
            prefs.quiet_hours_start = request.data['quiet_hours_start']
        if 'quiet_hours_end' in request.data:
            prefs.quiet_hours_end = request.data['quiet_hours_end']

        prefs.save()
        serializer = self.get_serializer(prefs)
        return Response(serializer.data)
