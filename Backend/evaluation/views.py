"""Owned evaluations; running state and model provenance are server controlled."""
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .access import visible_jobs, require_manage
from .constants import EvaluationFailure
from .models import EvaluationJob
from .resources import resolve_resources
from .serializers import EvaluationJobSerializer
from .services import create_evaluation, run_evaluation, recover_stale, normalized_parameters


class EvaluationJobViewSet(viewsets.ModelViewSet):
    serializer_class = EvaluationJobSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'job_id'

    def get_queryset(self):
        queryset = visible_jobs(self.request.user)
        recover_stale(queryset)
        return queryset

    def handle_exception(self, exc):
        if isinstance(exc, EvaluationFailure):
            return Response({'error': str(exc), 'error_code': exc.code}, status=exc.status)
        return super().handle_exception(exc)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_evaluation(request.user, serializer.validated_data)
        return Response(self.get_serializer(job).data, status=201)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        require_manage(request.user, instance)
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        current = {field: getattr(instance, field) for field in ('training_job_id', 'dataset_id', 'training_dataset_id',
            'model_path', 'test_dataset_path', 'name', 'parameters')}
        current.update(serializer.validated_data)
        # Changing an ID chooses that resource's registered path, not an old alias.
        if 'training_job_id' in serializer.validated_data and 'model_path' not in serializer.validated_data:
            current['model_path'] = ''
        if {'dataset_id', 'training_dataset_id'} & set(serializer.validated_data) and 'test_dataset_path' not in serializer.validated_data:
            current['test_dataset_path'] = ''
            if 'dataset_id' in serializer.validated_data:
                current['training_dataset_id'] = None
            else:
                current['dataset_id'] = None
        training, dataset, model, data = resolve_resources(request.user, current)
        from datasets.models import Dataset
        with transaction.atomic():
            locked = EvaluationJob.objects.select_for_update().get(pk=instance.pk)
            require_manage(request.user, locked)
            if locked.status == 'running':
                raise EvaluationFailure('运行中的评测不能编辑。', 'evaluation_conflict', 409)
            if locked.tenant_id != training.tenant_id:
                raise EvaluationFailure('已有评测不能转移到其他空间，请创建新评测。', 'tenant_mismatch', 403)
            locked.training_job, locked.tenant = training, training.tenant
            locked.dataset = dataset if isinstance(dataset, Dataset) else None
            locked.training_dataset = None if isinstance(dataset, Dataset) else dataset
            locked.model_path, locked.test_dataset_path = str(model), str(data)
            locked.name, locked.parameters = current['name'], normalized_parameters(training, current['parameters'])
            locked.status, locked.metrics, locked.error_code, locked.error_message = 'pending', {}, '', ''
            locked.started_at = locked.completed_at = locked.lease_expires_at = locked.claim_token = None
            locked.artifact_snapshot = {}
            locked.save()
        return Response(self.get_serializer(locked).data)

    def perform_destroy(self, instance):
        with transaction.atomic():
            locked = EvaluationJob.objects.select_for_update().get(pk=instance.pk)
            require_manage(self.request.user, locked)
            if locked.status == 'running':
                raise EvaluationFailure('运行中的评测不能删除。', 'evaluation_conflict', 409)
            locked.delete()

    @action(detail=True, methods=['post'])
    def run(self, request, job_id=None):
        if request.data:
            raise EvaluationFailure('运行使用已保存的评测配置，不接受临时模型路径。')
        job = self.get_object()
        job, status = run_evaluation(job.pk, request.user)
        return Response(self.get_serializer(job).data, status=status)

    @action(detail=True, methods=['post'])
    def cancel(self, request, job_id=None):
        instance = self.get_object()
        with transaction.atomic():
            job = EvaluationJob.objects.select_for_update().get(pk=instance.pk)
            require_manage(request.user, job)
            if job.status not in ('pending', 'running'):
                raise EvaluationFailure('评测已经结束。', 'evaluation_conflict', 409)
            job.status, job.completed_at = 'cancelled', timezone.now()
            job.error_code, job.error_message = 'cancelled', '评测已取消；不再接受迟到结果。'
            job.lease_expires_at = job.claim_token = None
            job.save(update_fields=['status', 'completed_at', 'error_code', 'error_message', 'lease_expires_at', 'claim_token'])
        return Response(self.get_serializer(job).data)
