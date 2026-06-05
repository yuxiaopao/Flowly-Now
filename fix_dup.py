"""Rebuild services.py - fix duplicate content"""
with open(r'e:\Flowly-now\Backend\nl_to_workflow\services.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line range to remove: old template body in _create_workflow_generation_prompt
# It's between the "## 工作流结构要求" section header and the "现在开始生成工作流" line
# within the old template = """ ... """ block
start_remove = None
end_remove = None
in_old_template = False
for i, line in enumerate(lines):
    # Find "## 工作流结构要求" - this is the start of the old template body
    if '## 工作流结构要求' in line and start_remove is None:
        # Make sure we're not in the module-level constant (line ~32)
        # The module-level one starts at line ~31
        # The old one is inside _create_workflow_generation_prompt, which starts around line ~1025
        if i > 100:  # It's in the method, not at top
            start_remove = i
    # Find the end of the old template body
    if start_remove is not None and '现在开始生成工作流' in line and i > start_remove + 10:
        end_remove = i + 1
        break

if start_remove is not None and end_remove is not None:
    print(f"Removing lines {start_remove+1} to {end_remove} ({end_remove - start_remove} lines)")
    new_lines = lines[:start_remove] + lines[end_remove:]
else:
    print("Could not find range to remove")
    new_lines = lines

# Write back
with open(r'e:\Flowly-now\Backend\nl_to_workflow\services.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Done. New line count: {len(new_lines)}")
