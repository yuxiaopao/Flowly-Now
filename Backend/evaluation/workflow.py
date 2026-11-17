"""The workflow node is an adapter to the same authorized evaluation runner."""
import logging
from rest_framework.exceptions import ValidationError
from .access import workflow_source
from .constants import EvaluationFailure
from .serializers import EvaluationJobSerializer
from .services import create_evaluation, run_evaluation

logger = logging.getLogger(__name__)


def run_evaluation_node(service, configuration, context):
    try:
        actor, workflow, node, execution = workflow_source(service.user_id, context)
        values = {'name': configuration.get('label') or node.name,
            'model_path': configuration.get('modelPath') or context.get('model_path') or '',
            'test_dataset_path': configuration.get('testDataset') or context.get('test_dataset') or context.get('dataset_path') or ''}
        for key, value in (('training_job_id', configuration.get('trainingJobId') or configuration.get('trainingRunId') or context.get('training_run_id')),
            ('dataset_id', configuration.get('datasetId')), ('training_dataset_id', configuration.get('trainingDatasetId'))):
            if value:
                values[key] = value
        parameters = dict(configuration.get('parameters') or {})
        for camel, snake in (('labelColumn', 'label_column'), ('features', 'features'), ('split', 'split'), ('imageSize', 'image_size')):
            if camel in configuration:
                if camel == 'labelColumn' and isinstance(configuration[camel], str) and not configuration[camel].strip():
                    continue
                parameters[snake] = configuration[camel]
        if configuration.get('metrics'):
            metrics = configuration['metrics']
            parameters['metrics'] = [value.strip() for value in metrics.split(',') if value.strip()] if isinstance(metrics, str) else metrics
        values['parameters'] = parameters
        serializer = EvaluationJobSerializer(data=values)
        serializer.is_valid(raise_exception=True)
        job = create_evaluation(actor, serializer.validated_data, (workflow, node, execution), configuration.get('_execution_deadline_at'))
        job, _ = run_evaluation(job.pk, actor)
        output = {'job_id': job.job_id, 'status': job.status, 'metrics': job.metrics,
            'model_path': job.model_path, 'test_dataset': job.test_dataset_path}
        if job.status != 'completed':
            return {'success': False, 'error': job.error_message, 'error_type': job.error_code, 'output': output}
        return {'success': True, 'output': output}
    except EvaluationFailure as exc:
        return {'success': False, 'error': str(exc), 'error_type': exc.code}
    except ValidationError as exc:
        return {'success': False, 'error': str(exc.detail), 'error_type': 'invalid_evaluation'}
    except Exception:
        logger.exception('Model evaluation failed')
        return {'success': False, 'error': '真实模型评测不可用，请检查已登记模型与测试数据。', 'error_type': 'evaluation_unavailable'}
