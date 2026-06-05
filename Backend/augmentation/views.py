"""
Views for augmentation app.
"""

import os
import uuid
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count
from django.utils import timezone

from .models import AugmentationJob
from .serializers import (
    AugmentationJobSerializer, AugmentationJobListSerializer,
    AugmentationJobCreateSerializer, AugmentationJobRunSerializer,
    AugmentationJobUpdateSerializer, AugmentationStatisticsSerializer
)
from .tasks import run_augmentation_task
from datasets.models import Dataset

logger = logging.getLogger(__name__)


class AugmentationJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AugmentationJob management.
    
    Provides CRUD operations for augmentation jobs including run, status, and statistics.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return jobs filtered by tenant and user access."""
        user = self.request.user
        queryset = AugmentationJob.objects.filter(
            Q(tenant__isnull=True) | Q(tenant__in=user.tenants.values_list('tenant', flat=True))
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        strategy = self.request.query_params.get('strategy')
        if strategy:
            queryset = queryset.filter(strategy=strategy)

        dataset_id = self.request.query_params.get('dataset')
        if dataset_id:
            queryset = queryset.filter(input_dataset_id=dataset_id)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(input_dataset__name__icontains=search) |
                Q(output_dataset__name__icontains=search)
            )

        return queryset.select_related('input_dataset', 'output_dataset', 'created_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return AugmentationJobListSerializer
        elif self.action == 'create':
            return AugmentationJobCreateSerializer
        elif self.action == 'run':
            return AugmentationJobRunSerializer
        elif self.action in ['update', 'partial_update']:
            return AugmentationJobUpdateSerializer
        return AugmentationJobSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def run(self, request):
        """
        Run an augmentation job.
        
        Creates a new augmentation job and starts processing.
        """
        serializer = AugmentationJobRunSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        dataset_id = data['dataset_id']

        try:
            dataset = Dataset.objects.get(id=dataset_id)
        except Dataset.DoesNotExist:
            return Response(
                {'error': f'数据集 {dataset_id} 不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not dataset.is_ready:
            return Response(
                {'error': '数据集尚未准备就绪'},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_name = data.get('output_name')
        if not output_name:
            output_name = f"{dataset.name}_augmented_{timezone.now().strftime('%Y%m%d%H%M%S')}"

        output_mode = data.get('output_mode', 'create_new')

        job = AugmentationJob.objects.create(
            input_dataset=dataset,
            strategy=data['strategy'],
            ratio=data['ratio'],
            transformations=data.get('transformations', []),
            output_mode=output_mode,
            output_name=output_name,
            original_count=dataset.row_count or 0,
            status='pending',
            created_by=request.user
        )

        try:
            run_augmentation_task.delay(str(job.id))
        except Exception as e:
            logger.warning(f"Celery not available, running synchronously: {e}")
            from .tasks import run_augmentation_task_sync
            run_augmentation_task_sync(str(job.id))

        return Response(
            AugmentationJobSerializer(job).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get augmentation job status and progress."""
        job = self.get_object()
        return Response({
            'id': str(job.id),
            'status': job.status,
            'status_display': job.get_status_display(),
            'progress': job.progress,
            'augmented_count': job.augmented_count,
            'original_count': job.original_count,
            'error_message': job.error_message,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'duration_seconds': job.duration_seconds,
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a running augmentation job."""
        job = self.get_object()

        if job.status not in ['pending', 'running']:
            return Response(
                {'error': '只能取消等待中或运行中的任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        job.mark_failed('用户取消')
        return Response({'message': '任务已取消'})

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed augmentation job."""
        job = self.get_object()

        if job.status != 'failed':
            return Response(
                {'error': '只能重试失败的任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        job.status = 'pending'
        job.error_message = ''
        job.progress = 0
        job.save()

        try:
            run_augmentation_task.delay(str(job.id))
        except Exception:
            from .tasks import run_augmentation_task_sync
            run_augmentation_task_sync(str(job.id))

        return Response(AugmentationJobSerializer(job).data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get augmentation statistics."""
        user = request.user
        queryset = AugmentationJob.objects.filter(
            Q(tenant__isnull=True) | Q(tenant__in=user.tenants.values_list('tenant', flat=True))
        )

        stats = queryset.aggregate(
            total_jobs=Count('id'),
            completed_jobs=Count('id', filter=Q(status='completed')),
            failed_jobs=Count('id', filter=Q(status='failed')),
            running_jobs=Count('id', filter=Q(status__in=['pending', 'running'])),
            total_augmented_samples=Sum('augmented_count'),
            total_original_samples=Sum('original_count'),
        )

        stats['total_augmented_samples'] = stats['total_augmented_samples'] or 0
        stats['total_original_samples'] = stats['total_original_samples'] or 0

        return Response(AugmentationStatisticsSerializer(stats).data)

    @action(detail=False, methods=['get'])
    def presets(self, request):
        """Get augmentation preset configurations."""
        presets = [
            {
                'id': 'image_classification',
                'name': '图像分类增强',
                'description': '适合图像分类任务的数据增强',
                'strategy': 'all',
                'ratio': 3.0,
                'transformations': [
                    'rotate', 'flip_horizontal', 'flip_vertical',
                    'brightness', 'contrast', 'saturation',
                    'gaussian_noise'
                ],
                'recommended_for': 'image_classification'
            },
            {
                'id': 'object_detection',
                'name': '目标检测增强',
                'description': '适合目标检测任务的数据增强',
                'strategy': 'geometric',
                'ratio': 5.0,
                'transformations': [
                    'rotate', 'flip_horizontal', 'flip_vertical',
                    'scale', 'crop', 'translate'
                ],
                'recommended_for': 'object_detection'
            },
            {
                'id': 'text_classification',
                'name': '文本分类增强',
                'description': '适合文本分类任务的数据增强',
                'strategy': 'all',
                'ratio': 2.0,
                'transformations': [
                    'synonym_replacement', 'random_swap', 'random_insertion'
                ],
                'recommended_for': 'text_classification'
            },
            {
                'id': 'tabular_balance',
                'name': '表格数据平衡',
                'description': '适合表格数据类别不平衡问题',
                'strategy': 'all',
                'ratio': 2.0,
                'transformations': [
                    'smote', 'random_noise', 'row_shuffle'
                ],
                'recommended_for': 'tabular_classification'
            },
        ]
        return Response(presets)
