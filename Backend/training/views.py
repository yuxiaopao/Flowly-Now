"""
Views for training app.
REST API for training jobs and datasets.
"""
import os
import re
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
    DatasetSerializer, DatasetCreateSerializer, DatasetListSerializer,
    YoloTrainingRunCreateSerializer, YoloTrainingRunDetailSerializer,
    YoloTrainingRunListSerializer, YoloTrainingRetrySerializer,
)
from .tasks import run_training_task, cancel_training_task
from tenants.access import get_accessible_tenant_ids

logger = logging.getLogger(__name__)

# Well-known Ultralytics plot filenames get a friendly Chinese label; anything else
# discovered on disk (val_batch*, train_batch*, custom callbacks, etc.) is labelled
# dynamically so new artifact types never require a code change.
YOLO_PLOT_LABELS = {
    'results.png': '训练曲线总览',
    'confusion_matrix.png': '混淆矩阵',
    'confusion_matrix_normalized.png': '归一化混淆矩阵',
    'F1_curve.png': 'F1 曲线',
    'P_curve.png': 'Precision 曲线',
    'R_curve.png': 'Recall 曲线',
    'PR_curve.png': 'PR 曲线',
    'BoxF1_curve.png': 'Box F1 曲线',
    'BoxP_curve.png': 'Box P 曲线',
    'BoxR_curve.png': 'Box R 曲线',
    'BoxPR_curve.png': 'Box PR 曲线',
    'MaskF1_curve.png': 'Mask F1 曲线',
    'MaskP_curve.png': 'Mask P 曲线',
    'MaskR_curve.png': 'Mask R 曲线',
    'MaskPR_curve.png': 'Mask PR 曲线',
    'labels.jpg': '标签分布',
    'labels_correlogram.jpg': '标签相关性',
}

# (regex, label template) — matched against filename stem when no exact label exists.
YOLO_PLOT_LABEL_PATTERNS = [
    (re.compile(r'^train_batch(\d+)$'), '训练批次预览 #{0}'),
    (re.compile(r'^val_batch(\d+)_labels$'), '验证批次标注 #{0}'),
    (re.compile(r'^val_batch(\d+)_pred$'), '验证批次预测 #{0}'),
    (re.compile(r'^val_batch(\d+)$'), '验证批次预览 #{0}'),
]

# Only image files directly inside the run directory are ever exposed; this regex
# blocks path traversal / hidden files while remaining format-agnostic.
SAFE_PLOT_FILENAME_RE = re.compile(r'^[A-Za-z0-9_\-]+\.(png|jpg|jpeg)$', re.IGNORECASE)


def _label_for_plot(filename: str) -> str:
    if filename in YOLO_PLOT_LABELS:
        return YOLO_PLOT_LABELS[filename]
    stem = os.path.splitext(filename)[0]
    for pattern, template in YOLO_PLOT_LABEL_PATTERNS:
        m = pattern.match(stem)
        if m:
            return template.format(*m.groups())
    return stem.replace('_', ' ')


def _discover_plot_files(run_dir):
    """Scan run_dir for any safe image file, newest-relevant ones first."""
    from pathlib import Path

    if not run_dir or not Path(run_dir).is_dir():
        return []

    found = []
    for entry in Path(run_dir).iterdir():
        if not entry.is_file():
            continue
        if not SAFE_PLOT_FILENAME_RE.match(entry.name):
            continue
        found.append(entry)

    def sort_key(p):
        # Curated overview charts first, then batch previews in natural order, then rest.
        priority = 0 if p.name in YOLO_PLOT_LABELS else 1
        return (priority, p.name)

    found.sort(key=sort_key)
    return found


def _resolve_yolo_run_dir(job: TrainingJob):
    """Resolve Ultralytics run directory from job weight paths or config."""
    from pathlib import Path

    weight_path = job.best_weight_path or job.model_path or ''
    if weight_path:
        wp = Path(weight_path)
        if wp.exists() and wp.parent.name == 'weights':
            return wp.parent.parent

    output_dir = (job.config or {}).get('output_dir') or ''
    if output_dir:
        base = Path(output_dir)
        if base.is_dir():
            for name in ('train', 'yolo_train', job.name or ''):
                candidate = base / name if name else base
                if candidate.is_dir() and (candidate / 'results.png').exists():
                    return candidate
            if (base / 'results.png').exists():
                return base
            for child in base.iterdir():
                if child.is_dir() and (child / 'results.png').exists():
                    return child
    return None


def _resolve_dataset_file_path(file_path):
    """Resolve dataset file path from stored value to an existing filesystem path."""
    if not file_path:
        return None
    if os.path.isabs(file_path) and os.path.exists(file_path):
        return file_path

    from django.conf import settings

    candidates = [
        file_path,
        os.path.join(settings.BASE_DIR, file_path),
        os.path.join(settings.BASE_DIR, 'data', file_path),
        os.path.join(settings.MEDIA_ROOT, file_path) if getattr(settings, 'MEDIA_ROOT', None) else None,
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return file_path


def _get_tenant(request):
    """Return the user's primary active tenant, or None."""
    ids = get_accessible_tenant_ids(request.user)
    if not ids:
        return None
    from tenants.models import Tenant
    return Tenant.objects.filter(id=ids[0]).first()


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
            from django.conf import settings

            config_dir = Path(settings.BASE_DIR) / 'data' / 'training_configs'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f'{job.id}.json'

            config_data = {
                'job_id': str(job.id),
                'framework': job.framework,
                'model_type': job.model_type,
                'training_kind': job.training_kind,
                'config': job.config,
                'dataset_id': job.dataset_id,
                'dataset_path': job.dataset_path,
                'hyperparameters': job.config.get('hyperparameters', {}),
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False)

            default_out = Path(settings.BASE_DIR) / 'data' / 'training_outputs' / str(job.id)
            output_dir = job.config.get('output_dir', str(default_out))
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
            from django.conf import settings

            config_dir = Path(settings.BASE_DIR) / 'data' / 'training_configs'
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f'{job.id}.json'

            config_data = {
                'job_id': str(job.id),
                'framework': job.framework,
                'model_type': job.model_type,
                'training_kind': job.training_kind,
                'config': job.config,
                'dataset_id': job.dataset_id,
                'dataset_path': job.dataset_path,
                'hyperparameters': job.config.get('hyperparameters', {}),
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False)

            default_out = Path(settings.BASE_DIR) / 'data' / 'training_outputs' / str(job.id)
            output_dir = job.config.get('output_dir', str(default_out))
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

    @action(detail=True, methods=['get'], url_path='artifact-manifest')
    def artifact_manifest(self, request, pk=None):
        """Return the stable model artifact manifest for generated-site nodes."""
        from .artifacts import build_model_artifact_manifest

        return Response(build_model_artifact_manifest(self.get_object()))

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

    @action(detail=False, methods=['get'], url_path='options')
    def options(self, request):
        """Return training strategy metadata (YOLO / CLIP / Transformer)."""
        from .options import get_training_options
        return Response(get_training_options())

    @action(detail=False, methods=['post'], url_path='analyze-dataset')
    def analyze_dataset(self, request):
        """Analyze dataset classes and distribution from payload."""
        from .options import analyze_dataset_payload

        def dataset_lookup(dataset_id):
            return Dataset.objects.filter(id=dataset_id).first()

        result = analyze_dataset_payload(request.data or {}, dataset_lookup=dataset_lookup)
        return Response(result)

    @action(detail=False, methods=['get'], url_path='gpu-info')
    def gpu_info(self, request):
        """Return server-side GPU availability for training configuration."""
        gpu_info = {
            'available': False,
            'name': None,
            'memory': None,
            'memory_total_mb': 0,
            'memory_free_mb': 0,
            'recommended_batch_size': 16,
            'recommendedBatchSize': 16,
        }
        try:
            import torch
            gpu_info['available'] = torch.cuda.is_available()
            if gpu_info['available']:
                props = torch.cuda.get_device_properties(0)
                total_mb = round(props.total_memory / 1024 / 1024)
                gpu_info.update({
                    'name': torch.cuda.get_device_name(0),
                    'memory': f'{total_mb}MB',
                    'memory_total_mb': total_mb,
                    'memory_free_mb': total_mb,
                    'recommended_batch_size': 64 if total_mb >= 8192 else 32,
                    'recommendedBatchSize': 64 if total_mb >= 8192 else 32,
                })
            gpu_info['torch_version'] = torch.__version__
        except ImportError:
            gpu_info['error'] = 'PyTorch not installed'
        except Exception as exc:
            gpu_info['error'] = str(exc)

        return Response(gpu_info)


class YoloTrainingRunViewSet(viewsets.ModelViewSet):
    """ViewSet for YOLO-specific training runs."""

    permission_classes = [permissions.IsAuthenticated]
    queryset = TrainingJob.objects.filter(training_kind='yolo')

    def get_queryset(self):
        queryset = TrainingJob.objects.filter(training_kind='yolo')

        if not self.request.user.is_superuser:
            tenant = _get_tenant(self.request)
            if tenant:
                queryset = queryset.filter(Q(tenant=tenant) | Q(created_by=self.request.user))
            else:
                queryset = queryset.filter(created_by=self.request.user)

        run_status = self.request.query_params.get('status')
        if run_status:
            queryset = queryset.filter(status=run_status)

        workflow_id = self.request.query_params.get('workflow')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)

        return queryset.select_related('workflow', 'node', 'execution', 'created_by', 'tenant').order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return YoloTrainingRunListSerializer
        if self.action == 'create':
            return YoloTrainingRunCreateSerializer
        return YoloTrainingRunDetailSerializer

    def perform_create(self, serializer):
        job = serializer.save(training_kind='yolo', framework='ultralytics', model_type='detection')

        try:
            import json
            from pathlib import Path

            config_dir = Path('e:/Flowly-now/Backend/data/training_configs')
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / f'{job.id}.json'

            config_data = {
                'job_id': str(job.id),
                'training_kind': 'yolo',
                'framework': job.framework,
                'model_type': job.model_type,
                'yolo_version': job.yolo_version,
                'model_variant': job.model_variant,
                'dataset_id': job.dataset_id,
                'dataset_path': job.dataset_path,
                'dataset_yaml_path': job.dataset_yaml_path,
                'dataset_source_mode': job.dataset_source_mode,
                'annotation_project_id': job.annotation_project_id,
                'class_names': job.class_names,
                'config': job.config,
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            output_dir = job.config.get('output_dir', f'e:/Flowly-now/Backend/data/training_outputs/{job.id}')
            run_training_task.delay(str(job.id), str(config_path), output_dir)
            logger.info(f"YOLO training task dispatched for job {job.id}")
        except Exception as e:
            logger.warning(f"Failed to dispatch YOLO training task: {e}")

    @action(detail=True, methods=['get'])
    def metrics_history(self, request, pk=None):
        job = self.get_object()
        return Response({
            'training_run_id': str(job.id),
            'status': job.status,
            'total_epochs': job.total_epochs,
            'series': {
                'loss_box': job.loss_box_history or [],
                'loss_cls': job.loss_cls_history or [],
                'loss_dfl': job.loss_dfl_history or [],
                'precision': job.precision_history or [],
                'recall': job.recall_history or [],
                'mAP50': job.map50_history or [],
                'mAP50_95': job.map50_95_history or [],
            },
            'metrics_history': job.metrics_history or [],
        })

    @action(detail=True, methods=['get'], url_path='artifact-manifest')
    def artifact_manifest(self, request, pk=None):
        """Return the stable model artifact manifest for generated-site nodes."""
        from .artifacts import build_model_artifact_manifest

        return Response(build_model_artifact_manifest(self.get_object()))

    @action(detail=True, methods=['get'])
    def plots(self, request, pk=None):
        """List all native Ultralytics plot/preview images produced so far for this run.

        Discovery is dynamic (not a fixed whitelist) so batch-preview images that only
        appear mid-training (val_batch*, train_batch*, etc.) show up as soon as
        Ultralytics writes them to disk — enabling live, ComfyUI-style image reveal.
        """
        job = self.get_object()
        run_dir = _resolve_yolo_run_dir(job)
        plots = []
        for path in _discover_plot_files(run_dir):
            plots.append({
                'name': path.name,
                'label': _label_for_plot(path.name),
                'size_bytes': path.stat().st_size,
                'modified_at': path.stat().st_mtime,
            })
        return Response({
            'training_run_id': str(job.id),
            'status': job.status,
            'run_dir': str(run_dir) if run_dir else '',
            'plots': plots,
        })

    @action(detail=True, methods=['get'], url_path='plot')
    def plot_image(self, request, pk=None):
        """Serve a training plot/preview image, guarded against path traversal."""
        job = self.get_object()
        name = (request.query_params.get('name') or 'results.png').strip()
        if not SAFE_PLOT_FILENAME_RE.match(name):
            return Response(
                {'error': {'code': 'INVALID_PLOT', 'message': '不支持的图表文件名'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        run_dir = _resolve_yolo_run_dir(job)
        if not run_dir:
            return Response(
                {'error': {'code': 'RUN_DIR_NOT_FOUND', 'message': '训练输出目录不存在'}},
                status=status.HTTP_404_NOT_FOUND,
            )
        from pathlib import Path
        run_dir = Path(run_dir).resolve()
        plot_path = (run_dir / name).resolve()
        if run_dir not in plot_path.parents or not plot_path.is_file():
            return Response(
                {'error': {'code': 'PLOT_NOT_FOUND', 'message': '请求的图表尚未生成'}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(open(plot_path, 'rb'), filename=name)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        job = self.get_object()
        if job.status not in ['queued', 'running']:
            return Response({'error': '只能取消排队中或训练中的任务'}, status=status.HTTP_400_BAD_REQUEST)

        cancel_training_task.delay(str(job.id))
        return Response({'training_run_id': str(job.id), 'status': 'cancelling', 'message': 'YOLO训练任务取消中'})

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        job = self.get_object()
        if job.status not in ['failed', 'cancelled', 'completed']:
            return Response({'error': '只能重试失败、已取消或已完成的任务'}, status=status.HTTP_400_BAD_REQUEST)

        retry_serializer = YoloTrainingRetrySerializer(data=request.data or {})
        retry_serializer.is_valid(raise_exception=True)
        retry_mode = retry_serializer.validated_data.get('mode', 'from_scratch')
        checkpoint_path = retry_serializer.validated_data.get('checkpoint_path', '')

        config = dict(job.config or {})
        config['retry_mode'] = retry_mode
        if checkpoint_path:
            config['checkpoint_path'] = checkpoint_path

        retry_job = TrainingJob.objects.create(
            name=f"{job.name or 'YOLO Training'} (Retry)",
            workflow=job.workflow,
            node=job.node,
            execution=job.execution,
            status='queued',
            training_kind='yolo',
            config=config,
            dataset_id=job.dataset_id,
            dataset_path=job.dataset_path,
            dataset_yaml_path=job.dataset_yaml_path,
            dataset_source_mode=job.dataset_source_mode,
            annotation_project_id=job.annotation_project_id,
            class_names=job.class_names,
            framework='ultralytics',
            model_type='detection',
            yolo_version=job.yolo_version,
            model_variant=job.model_variant,
            total_epochs=job.total_epochs,
            created_by=request.user,
            tenant=_get_tenant(request),
        )

        self.perform_create(type('SerializerWrapper', (), {'save': lambda *_args, **_kwargs: retry_job})())
        return Response({'new_training_run_id': str(retry_job.id), 'status': 'queued', 'message': 'YOLO训练任务已重新加入队列'})

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        job = self.get_object()
        artifact = request.query_params.get('artifact', 'pt')
        artifact_map = {
            'pt': job.best_weight_path or job.model_path,
            'last_pt': job.last_weight_path,
            'onnx': (job.exported_artifacts or {}).get('onnx', ''),
            'torchscript': (job.exported_artifacts or {}).get('torchscript', ''),
        }
        model_path = artifact_map.get(artifact, '')
        if not model_path:
            return Response({'error': {'code': 'ARTIFACT_NOT_READY', 'message': '请求的权重文件尚未生成'}}, status=status.HTTP_404_NOT_FOUND)
        if not os.path.exists(model_path):
            return Response({'error': {'code': 'ARTIFACT_NOT_FOUND', 'message': '请求的权重文件不存在'}}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(model_path, 'rb'), as_attachment=True, filename=os.path.basename(model_path))


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
        resolved_path = _resolve_dataset_file_path(dataset.file_path)

        if not resolved_path:
            return Response(
                {'error': '数据集文件路径不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        preview_data = []
        row_limit = int(request.query_params.get('limit', 100))

        try:
            if dataset.format == 'csv':
                import pandas as pd
                df = pd.read_csv(resolved_path, nrows=row_limit)
                preview_data = df.to_dict('records')
            elif dataset.format == 'json':
                import json
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        preview_data = data[:row_limit]
                    else:
                        preview_data = [data]
            else:
                return Response(
                    {'error': f'暂不支持 {dataset.format} 格式预览'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            columns = dataset.columns or []
            if not columns and preview_data and isinstance(preview_data[0], dict):
                columns = list(preview_data[0].keys())

            return Response({
                'columns': columns,
                'preview': preview_data,
                'total_rows': dataset.row_count or len(preview_data),
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
            resolved_path = _resolve_dataset_file_path(dataset.file_path)
            try:
                if dataset.format == 'csv' and resolved_path and os.path.exists(resolved_path):
                    import pandas as pd
                    df = pd.read_csv(resolved_path)
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
                elif dataset.format == 'json' and resolved_path and os.path.exists(resolved_path):
                    import json
                    with open(resolved_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    rows = data if isinstance(data, list) else [data]
                    stats['row_count'] = stats['row_count'] or len(rows)
                    stats['column_stats'] = {}
                    for col in dataset.columns or []:
                        values = [row.get(col) for row in rows if isinstance(row, dict)]
                        null_count = sum(1 for v in values if v is None or v == '')
                        unique_values = {str(v) for v in values if v is not None and v != ''}
                        sample = next((v for v in values if v not in (None, '')), '-')
                        stats['column_stats'][col] = {
                            'dtype': 'object',
                            'null_count': null_count,
                            'unique_count': len(unique_values),
                            'sample': sample if isinstance(sample, (str, int, float)) else str(sample),
                        }
            except Exception as e:
                logger.warning(f"Error calculating column stats: {str(e)}")

        return Response(stats)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download dataset source file."""
        dataset = self.get_object()
        resolved_path = _resolve_dataset_file_path(dataset.file_path)
        if not resolved_path or not os.path.exists(resolved_path):
            return Response({'error': '数据集文件不存在'}, status=status.HTTP_404_NOT_FOUND)
        filename = os.path.basename(resolved_path) or f"{dataset.name}.{dataset.format or 'bin'}"
        return FileResponse(open(resolved_path, 'rb'), as_attachment=True, filename=filename)
