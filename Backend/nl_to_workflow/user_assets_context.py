"""
User-owned training weights and generated sites for NL workflow enrichment.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def fetch_user_yolo_weights(user_id: Optional[int], limit: int = 5) -> List[Dict[str, Any]]:
    if not user_id:
        return []
    try:
        from training.models import TrainingJob

        qs = (
            TrainingJob.objects.filter(
                created_by_id=user_id,
                training_kind='yolo',
                status='completed',
            )
            .exclude(best_weight_path='')
            .order_by('-completed_at', '-created_at')[:limit]
        )
        items: List[Dict[str, Any]] = []
        for job in qs:
            metrics = job.metrics if isinstance(job.metrics, dict) else {}
            items.append({
                'id': str(job.id),
                'name': job.name,
                'best_weight_path': job.best_weight_path,
                'class_names': job.class_names or [],
                'yolo_version': job.yolo_version,
                'model_variant': job.model_variant,
                'total_epochs': job.total_epochs,
                'best_fitness': job.best_fitness,
                'metrics': {
                    'mAP50': metrics.get('mAP50') or metrics.get('map50'),
                    'precision': metrics.get('precision'),
                    'recall': metrics.get('recall'),
                },
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            })
        return items
    except Exception as exc:
        logger.debug('fetch_user_yolo_weights failed: %s', exc)
        return []


def pick_reusable_yolo_weight(
    user_id: Optional[int],
    description: str,
    *,
    class_names: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """Pick a completed weight to reuse unless user explicitly asks to retrain."""
    lower = (description or '').lower()
    retrain_hints = (
        '重新训练', '再训练', '从头训练', 'retrain', 'train again', 'from scratch', '全新训练',
    )
    if any(h in lower for h in retrain_hints):
        return None

    weights = fetch_user_yolo_weights(user_id, limit=10)
    if not weights:
        return None

    if class_names:
        wanted = {str(c).lower() for c in class_names}
        for w in weights:
            existing = {str(c).lower() for c in (w.get('class_names') or [])}
            if wanted and wanted == existing:
                return w

    return weights[0]


def build_user_assets_context_text(user_id: Optional[int]) -> str:
    weights = fetch_user_yolo_weights(user_id, limit=5)
    if not weights:
        return ''
    lines = ['【用户已有 YOLO 权重 — 可复用，避免重复训练】']
    for w in weights:
        m = w.get('metrics') or {}
        lines.append(
            f"- {w.get('name')} id={w.get('id')} classes={w.get('class_names')} "
            f"mAP50={m.get('mAP50')} path={w.get('best_weight_path')}"
        )
    return '\n'.join(lines)
