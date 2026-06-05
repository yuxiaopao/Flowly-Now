"""
Website Generator - generates deployable websites from trained ML models.
"""

from .classification import ClassificationGenerator
from .regression import RegressionGenerator
from .detection import DetectionGenerator
from .nlp import NLPGGenerator
from .base import BaseGenerator


def get_generator(website_type: str, config: dict) -> BaseGenerator:
    """
    Factory function to get the appropriate generator.
    """
    generator_map = {
        'classification': ClassificationGenerator,
        'nlp_classification': NLPGGenerator,
        'regression': RegressionGenerator,
        'detection': DetectionGenerator,
    }
    generator_cls = generator_map.get(website_type, ClassificationGenerator)
    return generator_cls(config)


__all__ = [
    'get_generator',
    'ClassificationGenerator',
    'RegressionGenerator',
    'DetectionGenerator',
    'NLPGGenerator',
    'BaseGenerator'
]
