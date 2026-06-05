"""
Views for training app.
REST API for training jobs and datasets.
"""
import os
import logging
from django.http import FileResponse, Http404
from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TrainingJob, Dataset
from .serializers import (
    TrainingJobSerializer, TrainingJobCreateSerializer,
    TrainingJobUpdateSerializer, TrainingJobListSerializer,
    DatasetSerializer, DatasetCreateSerializer, DatasetListSerializer
)
from .tasks import run_training_task

logger = logging.getLogger(__name__)


def _get_tenant(request):
    """Extract tenant from request user."""
    if hasattr(request.user, 'tenant'):
        return request.user.tenant
    return None


class TrainingJobViewSet(viewsets.ModelViewSet):
    """ViewSet for TrainingJob model."""

    permission_classes = [permissions.IsAuthenticated]
    queryset = TrainingJob.objects.all()

    def get_queryset(self):
        """Filter training jobs based on user and tenant."""
        queryset = TrainingJob.objects.all()

        if not self.request.user.is_superuser:
            tenant = _get_tenant(self.request)
            if tenant:
                queryset = queryset.filter(
                    Q(tenant=tenant) | Q(created_by=self.request.user)
                )
            else:
                queryset = queryset.filter(created_by=self.request.user)

        workflow_id = self.request.query_params.get('workflow')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)

        node_id = self.request.query_params.get('node')
        if node_id:
            queryset = queryset.filter(node_id=node_id)

        job_status = self.request.query_params.get('status')
        if job_status:
            queryset = queryset.filter(status=job_status)

        framework = self.request.query_params.get('framework')
        if framework:
            queryset = queryset.filter(framework=framework)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(error_message__icontains=search)
            )

        return queryset.select_related(
            'workflow', 'node', 'execution', 'created_by', 'tenant'
        ).order_by('-created_at')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return TrainingJobListSerializer
        elif self.action == 'create':
            return TrainingJobCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TrainingJobUpdateSerializer
        return TrainingJobSerializer

    def perform_create(self, serializer):
        """Create training job and dispatch Celery task."""
        job = serializer.save()

        # Dispatch Celery task for async training
        try:
            from .tasks import run_training_task
            import json
            from pathlib import Path

            # Build config path
            config_dir = Path('e:/Flowly-now/Backend/data/training_configs')
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f'{job.id}.json'

            config_data = {
                'job_id': str(job.id),
                'framework': job.framework,
                'model_type': job.model_type,
                'config': job.config,
                'dataset_id': job.dataset_id,
                'dataset_path': job.dataset_path,
                'hyperparameters': job.config.get('hyperparameters', {}),
            }
            with open(config_path, 'w') as f:
                json.dump(config_data, f)

            output_dir = job.config.get('output_dir', f'e:/Flowly-now/Backend/data/training_outputs/{job.id}')
            run_training_task.delay(str(job.id), str(config_path), output_dir)
            logger.info(f"Training task dispatched for job {job.id}")
        except Exception as e:
            logger.warning(f"Failed to dispatch training task: {e}")

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a training job."""
        job = self.get_object()

        if job.status not in ['queued', 'running']:
            return Response(
                {'error': '只能取消排队中或训练中的任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        job.mark_cancelled()
        return Response({
            'status': job.status,
            'message': '训练任务已取消'
        })

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed or cancelled training job."""
        job = self.get_object()

        if job.status not in ['failed', 'cancelled']:
            return Response(
                {'error': '只能重试失败或已取消的任务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        job.status = 'queued'
        job.error_message = ''
        job.completed_at = None
        job.progress = 0
        job.current_epoch = 0
        job.save()

        # Re-dispatch
        try:
            from .tasks import run_training_task
            import json
            from pathlib import Path

            config_dir = Path('e:/Flowly-now/Backend/data/training_configs')
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f'{job.id}.json'

            config_data = {
                'job_id': str(job.id),
                'framework': job.framework,
                'model_type': job.model_type,
                'config': job.config,
                'dataset_id': job.dataset_id,
                'dataset_path': job.dataset_path,
                'hyperparameters': job.config.get('hyperparameters', {}),
            }
            with open(config_path, 'w') as f:
                json.dump(config_data, f)

            output_dir = job.config.get('output_dir', f'e:/Flowly-now/Backend/data/training_outputs/{job.id}')
            run_training_task.delay(str(job.id), str(config_path), output_dir)
        except Exception as e:
            logger.warning(f"Failed to re-dispatch training task: {e}")

        return Response({
            'status': job.status,
            'message': '训练任务已重新加入队列'
        })

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the trained model file."""
        job = self.get_object()

        if not job.model_path:
            return Response(
                {'error': '模型文件不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        model_path = job.model_path
        if not os.path.exists(model_path):
            return Response(
                {'error': '模型文件未找到'},
                status=status.HTTP_404_NOT_FOUND
            )

        file_name = os.path.basename(model_path)
        response = FileResponse(
            open(model_path, 'rb'),
            as_attachment=True,
            filename=file_name
        )
        return response

    @action(detail=True, methods=['get'])
    def metrics_history(self, request, pk=None):
        """Get metrics history for a training job."""
        job = self.get_object()
        return Response({
            'metrics_history': job.metrics_history or [],
            'status': job.status,
            'total_epochs': job.total_epochs,
        })

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get aggregate statistics for training jobs."""
        queryset = self.get_queryset()

        status_counts = dict(
            queryset.values('status').annotate(
                count=Count('id')
            ).values_list('status', 'count')
        )

        total_count = sum(status_counts.values())
        completed_count = status_counts.get('completed', 0)
        failed_count = status_counts.get('failed', 0)

        avg_duration_seconds = None
        completed_jobs = queryset.filter(
            status='completed',
            started_at__isnull=False,
            completed_at__isnull=False
        )
        if completed_jobs.exists():
            total_seconds = 0
            count = 0
            for j in completed_jobs.only('started_at', 'completed_at'):
                if j.completed_at and j.started_at:
                    delta = j.completed_at - j.started_at
                    total_seconds += delta.total_seconds()
                    count += 1
            if count > 0:
                avg_duration_seconds = total_seconds / count

        return Response({
            'total': total_count,
            'by_status': {
                'queued': status_counts.get('queued', 0),
                'running': status_counts.get('running', 0),
                'completed': completed_count,
                'failed': failed_count,
                'cancelled': status_counts.get('cancelled', 0),
            },
            'avg_duration_seconds': avg_duration_seconds,
            'success_rate': (completed_count / total_count * 100) if total_count > 0 else 0
        })


class DatasetViewSet(viewsets.ModelViewSet):
    """ViewSet for Dataset model."""

    permission_classes = [permissions.IsAuthenticated]
    queryset = Dataset.objects.all()

    def get_queryset(self):
        """Filter datasets based on user and tenant."""
        queryset = Dataset.objects.all()

        if not self.request.user.is_superuser:
            tenant = _get_tenant(self.request)
            if tenant:
                queryset = queryset.filter(
                    Q(tenant=tenant) | Q(created_by=self.request.user)
                )
            else:
                queryset = queryset.filter(created_by=self.request.user)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        file_format = self.request.query_params.get('format')
        if file_format:
            queryset = queryset.filter(format=file_format)

        return queryset.select_related('created_by', 'tenant').order_by('-created_at')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return DatasetListSerializer
        elif self.action == 'create':
            return DatasetCreateSerializer
        return DatasetSerializer

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview first 100 rows of dataset."""
        dataset = self.get_object()

        if not dataset.file_path:
            return Response(
                {'error': '数据集文件路径不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        preview_data = []
        row_limit = int(request.query_params.get('limit', 100))

        try:
            if dataset.format == 'csv':
                import pandas as pd
                df = pd.read_csv(dataset.file_path, nrows=row_limit)
                preview_data = df.to_dict('records')
            elif dataset.format == 'json':
                import json
                with open(dataset.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        preview_data = data[:row_limit]
                    else:
                        preview_data = [data]

            return Response({
                'columns': dataset.columns,
                'preview': preview_data,
                'total_rows': dataset.row_count,
                'displayed_rows': len(preview_data)
            })
        except Exception as e:
            logger.error(f"Error previewing dataset: {str(e)}")
            return Response(
                {'error': f'预览失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get dataset statistics."""
        dataset = self.get_object()

        stats = {
            'name': dataset.name,
            'format': dataset.format,
            'size': dataset.size,
            'row_count': dataset.row_count,
            'columns': dataset.columns,
            'column_count': len(dataset.columns) if dataset.columns else 0,
            'created_at': dataset.created_at,
            'created_by': dataset.created_by.username if dataset.created_by else None
        }

        if dataset.columns and dataset.file_path:
            try:
                if dataset.format == 'csv':
                    import pandas as pd
                    df = pd.read_csv(dataset.file_path)
                    stats['column_stats'] = {}
                    for col in dataset.columns:
                        if col in df.columns:
                            col_data = df[col]
                            col_stats = {
                                'dtype': str(col_data.dtype),
                                'null_count': int(col_data.isnull().sum()),
                                'unique_count': int(col_data.nunique())
                            }
                            if pd.api.types.is_numeric_dtype(col_data):
                                col_stats.update({
                                    'min': float(col_data.min()) if not pd.isna(col_data.min()) else None,
                                    'max': float(col_data.max()) if not pd.isna(col_data.max()) else None,
                                    'mean': float(col_data.mean()) if not pd.isna(col_data.mean()) else None
                                })
                            stats['column_stats'][col] = col_stats
            except Exception as e:
                logger.warning(f"Error calculating column stats: {str(e)}")

        return Response(stats)
