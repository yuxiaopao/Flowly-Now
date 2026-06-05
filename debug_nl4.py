import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, r'e:\Flowly-now\Backend')
django.setup()

# Read the template directly from the file
with open(r'e:\Flowly-now\Backend\nl_to_workflow\services.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the template
import re
method_match = re.search(r'def _create_workflow_generation_prompt\(self.*?\n(.*?)\n        return template\.format\(', content, re.DOTALL)
method_body = method_match.group(1)
template_match = re.search(r'template\s*=\s*"""(.*?)"""', method_body, re.DOTALL)
template_text = template_match.group(1)

# Find lines with single { or } that aren't part of {{
lines = template_text.split('\n')
for i, line in enumerate(lines, 1):
    # Remove {{ and }} first
    cleaned = line.replace('{{', '').replace('}}', '')
    # Now find single { or }
    if '{' in cleaned or '}' in cleaned:
        print(f"Line {i}: {line.rstrip()}")
