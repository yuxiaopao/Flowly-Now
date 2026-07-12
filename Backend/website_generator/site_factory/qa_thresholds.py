"""QA gate evaluation per Docs/desktop-ml-site-factory/references/qa-threshold-matrix.md"""

from typing import Any, Dict, Optional, Tuple


def evaluate_metrics_gate(
    website_type: str,
    metrics: Dict[str, Any],
    qa_profile: str = 'default',
    validation_count: Optional[int] = None,
) -> Tuple[str, str, list]:
    """
    Returns (gate, summary_zh, recommendations).
    gate: green | yellow | red
    """
    recommendations = []
    vcount = validation_count or metrics.get('validation_count') or metrics.get('sample_count')

    if vcount is not None and vcount < 20:
        return 'yellow', '验证样本过少（<20），指标仅供参考，建议增加数据后重新训练。', [
            '扩充验证集至至少 50 张',
        ]

    wtype = (website_type or 'detection').lower()

    if wtype in ('detection', 'yolo'):
        map50 = _float_metric(metrics, 'map50', 'mAP50', 'map_50')
        if map50 is None:
            return 'yellow', '未提供 mAP50 指标，已完成结构与服务检查，建议补充验证集评估。', [
                '在训练节点或评估节点输出 metrics',
            ]
        if map50 >= 0.75:
            return 'green', f'检测模型 mAP50 为 {map50:.0%}，达到演示/上线参考标准。', []
        if map50 >= 0.50:
            rec = ['增加标注数据或训练轮次', '尝试更大基础权重（如 yolov8m）']
            if qa_profile == 'research':
                return 'yellow', f'检测模型 mAP50 为 {map50:.0%}，可演示但未达严格上线标准。', rec
            return 'yellow', f'检测模型 mAP50 为 {map50:.0%}，可预览但建议优化后再对外发布。', rec
        return 'red', f'检测模型 mAP50 为 {map50:.0%}，低于可用阈值，请回训练或检查数据集。', [
            '检查标注质量',
            '确认类别与数据集匹配',
        ]

    if wtype in ('classification', 'clip_classification'):
        acc = _float_metric(metrics, 'accuracy', 'top1_accuracy', 'acc')
        if acc is None:
            return 'yellow', '未提供分类准确率，已完成服务检查。', []
        if acc >= 0.90:
            return 'green', f'分类准确率 {acc:.0%}，表现良好。', []
        if acc >= 0.75:
            return 'yellow', f'分类准确率 {acc:.0%}，可演示使用。', ['考虑数据增强']
        return 'red', f'分类准确率 {acc:.0%}，建议重新训练。', []

    if wtype in ('clip_retrieval', 'retrieval'):
        r5 = _float_metric(metrics, 'r_at_5', 'rAt5', 'recall_at_5')
        if r5 is None:
            return 'yellow', '未提供 R@5 检索指标，已完成 API 检查。', []
        if r5 >= 0.80:
            return 'green', f'检索 R@5 为 {r5:.0%}，演示质量较好。', []
        if r5 >= 0.60:
            return 'yellow', f'检索 R@5 为 {r5:.0%}，可用但建议扩充图库或 fine-tune。', []
        return 'red', f'检索 R@5 为 {r5:.0%}，索引或模型需重做。', []

    return 'yellow', '未知网站类型，已完成基础检查。', []


def _float_metric(metrics: Dict[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        if key in metrics and metrics[key] is not None:
            val = float(metrics[key])
            if val > 1.0 and val <= 100.0:
                return val / 100.0
            return val
    return None
