import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, r'e:\Flowly-now\Backend')
django.setup()

from nl_to_workflow.services import NLToWorkflowService

service = NLToWorkflowService(user=None)

# Test with detailed error catching
try:
    result = service._create_workflow_generation_prompt("test workflow", None)
    print(f"Prompt created, length: {len(result)}")
except ValueError as e:
    print(f"ValueError: {e}")
    # Try to find which template placeholder is the issue
    # Get the prompt template
    import inspect
    source = inspect.getsource(service._create_workflow_generation_prompt)
    print("\n--- Template in source ---")
    # Find all {variable} patterns
    import re
    placeholders = re.findall(r'\{(\w+)\}', source)
    print(f"Placeholders found: {placeholders}")
