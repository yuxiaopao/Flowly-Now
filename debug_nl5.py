import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, r'e:\Flowly-now\Backend')
django.setup()

from nl_to_workflow.services import NLToWorkflowService

print("Creating NLToWorkflowService...")
service = NLToWorkflowService(user=None)
print(f"OK: model={service.model}")

print("\nTesting _create_workflow_generation_prompt...")
try:
    prompt = service._create_workflow_generation_prompt("test workflow", None)
    print(f"OK: prompt length = {len(prompt)}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

print("\nTesting generate_workflow...")
try:
    result = service.generate_workflow("test workflow")
    print(f"OK: keys = {list(result.keys())}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()

print("\nDone")
