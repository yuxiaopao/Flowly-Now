"""
Utility functions for annotation app.
"""

import logging
import csv
import io
import json

logger = logging.getLogger(__name__)


def initialize_items_from_dataset(project):
    """
    Load dataset rows into AnnotationItem records.
    """
    from .models import AnnotationItem

    dataset = project.dataset
    items_to_create = []

    if dataset.preview_data:
        for idx, row in enumerate(dataset.preview_data):
            if isinstance(row, dict):
                data_content = row
                data_id = f'{dataset.id}_{idx}'
            else:
                data_content = {'text': str(row)}
                data_id = f'{dataset.id}_{idx}'

            items_to_create.append(AnnotationItem(
                project=project,
                data_id=data_id,
                data_content=data_content,
                status='pending',
            ))

        AnnotationItem.objects.bulk_create(items_to_create, batch_size=500)
        project.total_items = len(items_to_create)
        project.save(update_fields=['total_items'])

        return {'success': True, 'count': len(items_to_create)}

    return {'success': False, 'error': 'No preview data available'}


def generate_pre_labels(project):
    """
    Generate AI pre-labels for all pending items.
    Uses the configured LLM model.
    """
    from .models import AnnotationItem
    from workflows.services.langchain_service import langchain_service

    pending_items = project.items.filter(status='pending')
    labeled_count = 0

    model_id = project.model_id or 'gpt-4o-mini'

    for item in pending_items:
        text_content = item.data_content.get('text', '')
        if not text_content:
            continue

        try:
            prompt = (
                f"Classify the following text into exactly one of these labels: {', '.join(project.labels)}.\n\n"
                f"Text: {text_content}\n\n"
                f"Only respond with the label name, nothing else."
            )

            result = langchain_service.execute_node(
                'llm',
                {
                    'prompt': prompt,
                    'model': model_id,
                    'temperature': 0.1,
                    'max_tokens': 50,
                },
                {}
            )

            if result.get('success'):
                output = result.get('output', {})
                predicted_label = output.get('text', '').strip().strip('"\'')
                if predicted_label in project.labels:
                    item.pre_label = predicted_label
                    item.save()
                    labeled_count += 1

        except Exception as e:
            logger.error(f"Pre-labeling failed for item {item.id}: {str(e)}")
            continue

    return {'success': True, 'labeled_count': labeled_count}


def export_annotations(project, format='json'):
    """
    Export annotations as JSON or CSV.
    """
    from .models import AnnotationItem

    annotated_items = project.items.filter(status='annotated')

    if format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['data_id', 'text', 'label', 'pre_label', 'annotated_by', 'annotated_at'])
        for item in annotated_items:
            writer.writerow([
                item.data_id,
                item.data_content.get('text', ''),
                item.label,
                item.pre_label,
                item.annotated_by.username if item.annotated_by else '',
                item.annotated_at.isoformat() if item.annotated_at else '',
            ])
        return output.getvalue()

    data = []
    for item in annotated_items:
        data.append({
            'id': str(item.id),
            'data_id': item.data_id,
            'data_content': item.data_content,
            'label': item.label,
            'pre_label': item.pre_label,
            'annotated_by': item.annotated_by.username if item.annotated_by else None,
            'annotated_at': item.annotated_at.isoformat() if item.annotated_at else None,
        })

    return json.dumps({
        'project': str(project.id),
        'annotation_type': project.annotation_type,
        'labels': project.labels,
        'items': data,
        'total': len(data),
    }, ensure_ascii=False, indent=2)


def export_image_text_pairs(project):
    """
    Export annotated items as image_text_pairs JSONL (M4.3).
    Each line: {"image": "...", "text": "..."}
    """
    from .models import AnnotationItem

    pairs = []
    for item in AnnotationItem.objects.filter(project=project, status='annotated'):
        content = item.data_content if isinstance(item.data_content, dict) else {}
        image = (
            content.get('image')
            or content.get('image_path')
            or content.get('file')
            or content.get('path')
            or ''
        ).strip()
        text = (
            content.get('text')
            or content.get('caption')
            or content.get('description')
            or item.label
            or ''
        ).strip()
        if image and text:
            pairs.append({'image': image, 'text': text})

    if not pairs:
        return {
            'success': False,
            'error': '无可导出的图文对（需已标注项且 data_content 含 image + text/caption/label）',
        }

    content = '\n'.join(json.dumps(p, ensure_ascii=False) for p in pairs)
    return {
        'success': True,
        'format': 'image_text_pairs',
        'pair_count': len(pairs),
        'content': content,
        'pairs': pairs,
    }
