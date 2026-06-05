"""
Features API Views
"""
import json
import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse

from .models import SystemFeature, FeatureAuditLog
from .serializers import (
    SystemFeatureSerializer,
    SystemFeatureUpdateSerializer,
    FeatureAuditLogSerializer,
)
from .services.feature_service import get_feature_service

logger = logging.getLogger(__name__)


class SystemFeatureViewSet(viewsets.ModelViewSet):
    queryset = SystemFeature.objects.select_related('category').all()
    lookup_field = 'key'
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('partial_update', 'update'):
            return SystemFeatureUpdateSerializer
        return SystemFeatureSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'categories'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    def get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def partial_update(self, request, key=None):
        try:
            feature = SystemFeature.objects.get(key=key)
        except SystemFeature.DoesNotExist:
            return Response({'error': f"Feature '{key}' not found"}, status=status.HTTP_404_NOT_FOUND)

        if feature.is_readonly:
            return Response({'error': '此功能为只读，禁止修改'}, status=status.HTTP_403_FORBIDDEN)

        serializer = SystemFeatureUpdateSerializer(feature, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            get_feature_service()._log_change(
                feature, 'update',
                feature.value,
                serializer.validated_data.get('value'),
                request.user,
                self.get_client_ip(request),
                request.data.get('reason', ''),
            )
            get_feature_service().invalidate(key)
            return Response(SystemFeatureSerializer(feature).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='categories')
    def categories(self, request):
        data = get_feature_service().get_all_categories_with_features()
        return Response(data)

    @action(detail=True, methods=['post'], url_path='toggle')
    def toggle(self, request, key=None):
        try:
            feature = SystemFeature.objects.get(key=key)
        except SystemFeature.DoesNotExist:
            return Response({'error': f"Feature '{key}' not found"}, status=status.HTTP_404_NOT_FOUND)

        if feature.value_type != 'boolean':
            return Response({'error': '只有布尔类型的开关才支持切换'}, status=status.HTTP_400_BAD_REQUEST)
        if feature.is_readonly:
            return Response({'error': '此功能为只读，禁止修改'}, status=status.HTTP_403_FORBIDDEN)

        new_feature = get_feature_service().toggle(key, request.user, self.get_client_ip(request))
        return Response({
            'key': key,
            'old_value': not new_feature.get_value(),
            'new_value': new_feature.get_value(),
            'display_value': new_feature.get_display_value(),
        })

    @action(detail=True, methods=['post'], url_path='reset')
    def reset(self, request, key=None):
        try:
            new_feature = get_feature_service().reset(key, request.user, self.get_client_ip(request))
            return Response(SystemFeatureSerializer(new_feature).data)
        except SystemFeature.DoesNotExist:
            return Response({'error': f"Feature '{key}' not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='audit')
    def audit(self, request):
        key = request.query_params.get('key')
        limit = int(request.query_params.get('limit', 100))
        qs = FeatureAuditLog.objects.select_related('feature', 'changed_by').order_by('-created_at')
        if key:
            qs = qs.filter(feature__key=key)
        logs = list(qs[:limit])
        return Response(FeatureAuditLogSerializer(logs, many=True).data)
