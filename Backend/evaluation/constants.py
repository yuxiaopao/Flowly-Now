"""Evaluation limits and supported, deterministic metric names."""
CLASSIFICATION_METRICS = ('accuracy', 'precision', 'recall', 'f1', 'auc')
DETECTION_METRICS = ('precision', 'recall', 'mAP50', 'mAP50_95')
DEFAULT_METRICS = CLASSIFICATION_METRICS[:4]
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_LEASE_SECONDS = 330
POLL_SECONDS = .2
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_DATA_BYTES = 512 * 1024 * 1024
MAX_SAMPLES = 20000
MAX_FEATURES = 4096
MAX_MODEL_PARAMETERS = 50000000
MAX_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 16000000
MAX_ANNOTATION_LINE_CHARS = 100000
ACTIVE_TEAM_STATUSES = ('active', 'trial')
IMAGE_EXTENSIONS = frozenset(('.jpg', '.jpeg', '.png', '.bmp', '.webp'))


class EvaluationFailure(Exception):
    def __init__(self, message, code='invalid_evaluation', status=400):
        super().__init__(message)
        self.code, self.status = code, status
