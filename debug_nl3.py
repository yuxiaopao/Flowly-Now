import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, r'e:\Flowly-now\Backend')
django.setup()

# Read the template directly from the file
with open(r'e:\Flowly-now\Backend\nl_to_workflow\services.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the template between _create_workflow_generation_prompt and template.format
import re

# Find the method
method_match = re.search(r'def _create_workflow_generation_prompt\(self.*?\n(.*?)\n        return template\.format\(', content, re.DOTALL)
if not method_match:
    print("Method not found")
    sys.exit(1)

method_body = method_match.group(1)
print(f"Method body length: {len(method_body)}")

# Find the template variable assignment
template_match = re.search(r'template\s*=\s*"""(.*?)"""', method_body, re.DOTALL)
if not template_match:
    print("Template not found")
    sys.exit(1)

template_text = template_match.group(1)

# Check which format placeholder might cause the issue
# Valid placeholders
valid_placeholders = ['description', 'node_types', 'fallback_context']

# Look for unescaped format placeholders in template
lines = template_text.split('\n')
for i, line in enumerate(lines, 1):
    # Find single { followed by a word and }
    # But NOT {{ or }}
    matches = re.findall(r'(?<!{)\{([^}]+)\}(?!})', line)
    if matches:
        for m in matches:
            if m not in valid_placeholders:
                print(f"Line {i}: UNEXPECTED placeholder '{{{m}}}': {line.strip()[:100]}")

print("Check complete")
