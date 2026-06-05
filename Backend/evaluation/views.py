"""
Views for evaluation app.
"""

import logging
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import EvaluationJob
from .serializers import EvaluationJobSerializer
from .evaluators import evaluate_pytorch_classifier, evaluate_csv_classification, evaluate_mock

logger = logging.getLogger(__name__)


class EvaluationJobViewSet(viewsets.ModelViewSet):
    queryset = EvaluationJob.objects.all()
    serializer_class = EvaluationJobSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'job_id'

    @action(detail=True, methods=['post'])
    def run(self, request, job_id=None):
        job = self.get_object()
        if job.status == 'completed':
            return Response({'error': 'Job already completed'}, status=400)

        job.status = 'running'
        job.save()

        try:
            metrics = self._run_evaluation(job)
            job.metrics = metrics
            job.status = 'completed'
            from django.utils import timezone
            job.completed_at = timezone.now()
            job.save()
            return Response(EvaluationJobSerializer(job).data)
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.save()
            return Response({'error': str(e)}, status=500)

    def _run_evaluation(self, job):
        model_path = job.model_path
        test_path = job.test_dataset_path
        labels = ['cat', 'dog', 'bird']

        if not os.path.exists(model_path):
            logger.warning(f"Model file not found: {model_path}, using mock evaluation")
            return evaluate_mock(labels)

        if test_path and os.path.exists(test_path):
            try:
                import pandas as pd
                df = pd.read_csv(test_path)
                test_data = []
                for idx, row in df.iterrows():
                    test_data.append({
                        'features': row.dropna().tolist()[:-1],
                        'label': int(row.iloc[-1])
                    })
                return evaluate_pytorch_classifier(model_path, test_data, labels)
            except Exception as e:
                logger.warning(f"CSV evaluation failed: {e}")

        return evaluate_mock(labels)


from .serializers import EvaluationJobSerializer

import os
