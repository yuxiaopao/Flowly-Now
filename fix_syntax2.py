with open(r'e:\Flowly-now\Backend\nl_to_workflow\services.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines with 5 consecutive } (0-indexed: 861, 862, 888, 912, 913, 914)
fixes = {
    861: None,  # Line 862 - 回复感谢, keep "config": {{...}}}} as "config": {{...}}}
    862: None,  # Line 863 - 转人工
    888: None,  # Line 889 - 查询天气API
    912: None,  # Line 913 - 查询数据库
    913: None,  # Line 914 - 查询API
    914: None,  # Line 915 - 查询缓存
}

# For each line, find 5 consecutive } and replace with 4
import re
for lineno in list(fixes.keys()):
    line = lines[lineno]
    # Find pattern: 5 consecutive } followed by , (with optional whitespace)
    # In the template: }}}}}}, should become }}}},,
    # The last comma is part of the list item separator
    # Pattern: 5 } followed by , -> replace with 4 } followed by ,
    new_line = re.sub(r'\}{5}(,)', r'}}}}\1', line)
    if new_line != line:
        lines[lineno] = new_line
        print(f'Fixed line {lineno+1}: {repr(line[-80:])} -> {repr(new_line[-80:])}')
    else:
        print(f'No change needed line {lineno+1}')

with open(r'e:\Flowly-now\Backend\nl_to_workflow\services.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Done')
