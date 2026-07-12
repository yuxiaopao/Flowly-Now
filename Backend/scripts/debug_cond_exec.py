import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from workflows.models import Workflow, WorkflowExecution
from workflows.services.workflow_executor import WorkflowExecutor

wf = Workflow.objects.get(id="e1690129-6c31-4603-a58c-4f10342c7fda")
ex = WorkflowExecution.objects.create(workflow=wf, status="pending", input_data={})
try:
    WorkflowExecutor(wf, ex).execute()
    print("status", ex.status, "error", ex.error_message)
except Exception as e:
    import traceback
    traceback.print_exc()
