import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, r'e:\Flowly-now\Backend')
django.setup()

from nl_to_workflow.services import NLToWorkflowService

print("Creating NLToWorkflowService...")
try:
    service = NLToWorkflowService(user=None)
    print(f"Service created: model={service.model}, temp={service.temperature}")
except Exception as e:
    print(f"ERROR in __init__: {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()

print("\nTesting generate_workflow with mock...")
try:
    result = service.generate_workflow("test workflow")
    print(f"Result keys: {list(result.keys())}")
except Exception as e:
    print(f"ERROR in generate_workflow: {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()

print("\nTesting generate_workflow_streaming...")
try:
    chunks = list(service.generate_workflow_streaming("test"))
    print(f"Got {len(chunks)} chunks")
except Exception as e:
    print(f"ERROR in streaming: {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()

print("\nDone")
