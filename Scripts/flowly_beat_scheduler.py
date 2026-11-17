"""A local Beat scheduler records successful ticks, rather than process liveness."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

from celery.beat import PersistentScheduler
import psutil

HEARTBEAT_INTERVAL_SECONDS = 5


class ObservedPersistentScheduler(PersistentScheduler):
    def tick(self, *args, **kwargs):
        delay = super().tick(*args, **kwargs)
        root = Path(os.environ['FLOWLY_SERVICE_WORKSPACE']).resolve(strict=True)
        filename = root / '.cache' / 'local-services' / 'beat-heartbeat.json'
        if filename.resolve() != filename or Path.cwd().resolve() != root / 'Backend':
            raise RuntimeError('Beat 工作区或心跳位置无效。')
        process = psutil.Process()
        value = {'event': 'scheduler_tick', 'workspace_id': hashlib.sha256(os.path.normcase(str(root)).encode()).hexdigest()[:16],
                 'pid': process.pid, 'created_at': process.create_time(), 'observed_at': time.time()}
        descriptor, temporary = tempfile.mkstemp(dir=filename.parent, prefix='beat-heartbeat-', suffix='.tmp')
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(value, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, filename)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return min(HEARTBEAT_INTERVAL_SECONDS, max(0, delay if delay is not None else 1))
