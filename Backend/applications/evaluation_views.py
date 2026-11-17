"""Nested, application-scoped test suites and immutable evaluation evidence."""
import copy
import json
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from . import evaluation_constants as limits
from .evaluation_serializers import (SuiteSerializer, SuiteWriteSerializer, CaseSerializer, CaseWriteSerializer,
    StartRunSerializer, EvaluationRunSerializer, EvaluationRunDetailSerializer)
from .evaluation_service import start_run, recover_run, cancel_run, compare_runs
from .models import Application, ApplicationTestSuite, ApplicationTestCase, ApplicationEvaluationRun
from .services import ApplicationFailure


def suite_export_payload(suite):
    return {'type': 'flowly_application_test_suite', 'schema_version': limits.EXPORT_SCHEMA_VERSION,
        'suite': {'name': suite.name, 'description': suite.description},
        'cases': list(suite.cases.values('name', 'input_data', 'assertions', 'enabled', 'position'))}


def validate_suite_size(suite):
    if len(json.dumps(suite_export_payload(suite), ensure_ascii=False, allow_nan=False).encode()) > limits.MAX_IMPORT_BYTES:
        raise ValidationError('测试集内容超过可导入导出的总大小上限，请拆分测试集。')


class ApplicationEvaluationActions:
    def _lock_evaluation_application(self, application):
        locked = get_object_or_404(Application.objects.select_for_update(), pk=application.pk, is_deleted=False)
        self.require_edit(locked)
        return locked

    def _suite(self, application, identity, *, lock=False):
        query = ApplicationTestSuite.objects.select_for_update() if lock else ApplicationTestSuite.objects
        return get_object_or_404(query, pk=serializers.UUIDField().run_validation(identity), application=application, is_deleted=False)

    def _run(self, application, identity):
        run = get_object_or_404(ApplicationEvaluationRun.objects.select_related('application__owner', 'application__tenant', 'suite', 'release'),
            pk=serializers.UUIDField().run_validation(identity), application=application)
        return recover_run(run)

    @action(detail=True, methods=['get', 'post'], url_path='test-suites')
    def test_suites(self, request, pk=None):
        application = self.get_object()
        if request.method == 'GET':
            return self.paginate_values(application.test_suites.filter(is_deleted=False), SuiteSerializer)
        self.require_edit(application)
        form = SuiteWriteSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        with transaction.atomic():
            application = self._lock_evaluation_application(application)
            if application.test_suites.filter(is_deleted=False).count() >= getattr(settings, 'APPLICATION_MAX_TEST_SUITES', limits.MAX_SUITES):
                raise ValidationError(limits.MESSAGES['suite_limit'])
            suite = ApplicationTestSuite.objects.create(application=application, created_by=request.user, **form.validated_data)
        return Response(SuiteSerializer(suite).data, status=201)

    @action(detail=True, methods=['get', 'patch', 'delete'], url_path=r'test-suites/(?P<suite_id>[^/.]+)')
    def test_suite_detail(self, request, pk=None, suite_id=None):
        application = self.get_object()
        if request.method == 'GET':
            return Response(SuiteSerializer(self._suite(application, suite_id)).data)
        self.require_edit(application)
        with transaction.atomic():
            application = self._lock_evaluation_application(application)
            suite = self._suite(application, suite_id, lock=True)
            if request.method == 'DELETE':
                if Application.objects.filter(pk=application.pk, required_evaluation_suite=suite).exists():
                    raise ApplicationFailure(limits.MESSAGES['required_suite'], 'required_suite', 409)
                for run in suite.runs.filter(status__in=limits.ACTIVE_RUN_STATUSES):
                    recover_run(run)
                if suite.runs.filter(status__in=limits.ACTIVE_RUN_STATUSES).exists():
                    raise ApplicationFailure(limits.MESSAGES['suite_running'], 'suite_running', 409)
                suite.is_deleted = True
            else:
                form = SuiteWriteSerializer(data=request.data, partial=True)
                form.is_valid(raise_exception=True)
                for key, value in form.validated_data.items():
                    setattr(suite, key, value)
            suite.revision += 1
            suite.save()
            validate_suite_size(suite)
        return Response(status=204) if request.method == 'DELETE' else Response(SuiteSerializer(suite).data)

    @action(detail=True, methods=['get', 'post'], url_path=r'test-suites/(?P<suite_id>[^/.]+)/cases')
    def test_cases(self, request, pk=None, suite_id=None):
        application = self.get_object()
        if request.method == 'GET':
            return self.paginate_values(self._suite(application, suite_id).cases.all(), CaseSerializer)
        self.require_edit(application)
        form = CaseWriteSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = copy.deepcopy(form.validated_data)
        source_id = data.pop('from_request_id', None)
        if source_id:
            data['input_data'] = copy.deepcopy(get_object_or_404(application.requests, pk=source_id).input_data)
        with transaction.atomic():
            application = self._lock_evaluation_application(application)
            suite = self._suite(application, suite_id, lock=True)
            if suite.cases.count() >= getattr(settings, 'APPLICATION_MAX_TEST_CASES', limits.MAX_CASES):
                raise ValidationError(limits.MESSAGES['case_limit'])
            case = ApplicationTestCase.objects.create(suite=suite, **data)
            validate_suite_size(suite)
            suite.revision += 1
            suite.save(update_fields=['revision', 'updated_at'])
        return Response(CaseSerializer(case).data, status=201)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'test-suites/(?P<suite_id>[^/.]+)/cases/(?P<case_id>[^/.]+)')
    def test_case_detail(self, request, pk=None, suite_id=None, case_id=None):
        application = self.get_object()
        self.require_edit(application)
        with transaction.atomic():
            application = self._lock_evaluation_application(application)
            suite = self._suite(application, suite_id, lock=True)
            case = get_object_or_404(suite.cases, pk=serializers.UUIDField().run_validation(case_id))
            if request.method == 'DELETE':
                case.delete()
            else:
                form = CaseWriteSerializer(data=request.data, partial=True)
                form.is_valid(raise_exception=True)
                data = copy.deepcopy(form.validated_data)
                source_id = data.pop('from_request_id', None)
                if source_id:
                    data['input_data'] = copy.deepcopy(get_object_or_404(application.requests, pk=source_id).input_data)
                for key, value in data.items():
                    setattr(case, key, value)
                case.save()
                validate_suite_size(suite)
            suite.revision += 1
            suite.save(update_fields=['revision', 'updated_at'])
        return Response(status=204) if request.method == 'DELETE' else Response(CaseSerializer(case).data)

    @action(detail=True, methods=['post'], url_path='test-suites-import')
    def import_test_suite(self, request, pk=None):
        application = self.get_object()
        self.require_edit(application)
        payload = request.data
        if not isinstance(payload, dict) or set(payload) != {'type', 'schema_version', 'suite', 'cases'} or payload.get('type') != 'flowly_application_test_suite' or type(payload.get('schema_version')) is not int or payload.get('schema_version') != limits.EXPORT_SCHEMA_VERSION:
            raise ValidationError(limits.MESSAGES['import'])
        try:
            size = len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode())
        except (ValueError, TypeError):
            raise ValidationError(limits.MESSAGES['import'])
        if size > limits.MAX_IMPORT_BYTES:
            raise ValidationError('导入文件超过服务端大小上限。')
        header = SuiteWriteSerializer(data=payload['suite'])
        header.is_valid(raise_exception=True)
        rows = payload.get('cases')
        if not isinstance(rows, list) or not rows or len(rows) > getattr(settings, 'APPLICATION_MAX_TEST_CASES', limits.MAX_CASES):
            raise ValidationError(limits.MESSAGES['case_limit'])
        parsed = []
        for row in rows:
            if not isinstance(row, dict) or 'from_request_id' in row:
                raise ValidationError(limits.MESSAGES['import'])
            case_form = CaseWriteSerializer(data=row)
            case_form.is_valid(raise_exception=True)
            parsed.append(case_form.validated_data)
        with transaction.atomic():
            application = self._lock_evaluation_application(application)
            if application.test_suites.filter(is_deleted=False).count() >= getattr(settings, 'APPLICATION_MAX_TEST_SUITES', limits.MAX_SUITES):
                raise ValidationError(limits.MESSAGES['suite_limit'])
            suite = ApplicationTestSuite.objects.create(application=application, created_by=request.user, **header.validated_data)
            ApplicationTestCase.objects.bulk_create([ApplicationTestCase(suite=suite, **data) for data in parsed])
            validate_suite_size(suite)
        return Response(SuiteSerializer(suite).data, status=201)

    @action(detail=True, methods=['get'], url_path=r'test-suites/(?P<suite_id>[^/.]+)/export')
    def export_test_suite(self, request, pk=None, suite_id=None):
        suite = self._suite(self.get_object(), suite_id)
        content = suite_export_payload(suite)
        response = JsonResponse(content, json_dumps_params={'ensure_ascii': False, 'allow_nan': False})
        response['Content-Disposition'] = f'attachment; filename="application-tests-{suite.pk}.json"'
        response['Cache-Control'] = 'private, no-store'
        return response

    @action(detail=True, methods=['get', 'post'], url_path='evaluation-runs')
    def evaluation_runs(self, request, pk=None):
        application = self.get_object()
        if request.method == 'GET':
            rows = application.evaluation_runs.select_related('application__owner', 'application__tenant', 'suite', 'release')
            suite_id = request.query_params.get('suite_id')
            if suite_id:
                rows = rows.filter(suite_id=serializers.UUIDField().run_validation(suite_id))
            for run in rows.filter(status__in=limits.ACTIVE_RUN_STATUSES):
                recover_run(run)
            return self.paginate_values(rows, EvaluationRunSerializer)
        self.require_edit(application)
        form = StartRunSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        token = request.headers.get('Idempotency-Key')
        if token is not None and (not token.strip() or len(token) > 128):
            raise ValidationError('Idempotency-Key 需要 1 至 128 个字符。')
        run, created = start_run(application, request.user, form.validated_data, token)
        payload = EvaluationRunDetailSerializer(run).data
        status_code = 503 if run.error_code == 'queue_unavailable' else 202 if run.status in limits.ACTIVE_RUN_STATUSES else 201 if created else 200
        if status_code == 503:
            return Response({'code': 503, 'message': run.error_message, 'data': payload, 'errors': {'reason': run.error_code}}, status=503)
        return Response(payload, status=status_code)

    @action(detail=True, methods=['get'], url_path=r'evaluation-runs/(?P<run_id>[^/.]+)')
    def evaluation_run_detail(self, request, pk=None, run_id=None):
        return Response(EvaluationRunDetailSerializer(self._run(self.get_object(), run_id)).data)

    @action(detail=True, methods=['post'], url_path=r'evaluation-runs/(?P<run_id>[^/.]+)/cancel')
    def cancel_evaluation_run(self, request, pk=None, run_id=None):
        application = self.get_object()
        self.require_edit(application)
        if request.data:
            raise ValidationError('取消操作不接受额外字段。')
        return Response(EvaluationRunDetailSerializer(cancel_run(self._run(application, run_id))).data)

    @action(detail=True, methods=['get'], url_path=r'evaluation-runs/(?P<run_id>[^/.]+)/compare')
    def compare_evaluation_runs(self, request, pk=None, run_id=None):
        application = self.get_object()
        current = self._run(application, run_id)
        baseline = self._run(application, request.query_params.get('baseline_id'))
        return Response(compare_runs(current, baseline))
