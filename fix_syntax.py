with open(r'e:\Flowly-now\Backend\nl_to_workflow\services.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the three problematic code template lines
fixes = [
    ('"code": "def format_weather(data):\\\\n    return f\'{{data.city}}今天气温{{data.temp}}度\'"}}}}},', 
     '"code": "def format_weather(data):\\\\n    return f\'{{data.city}}今天气温{{data.temp}}度\'"}}}},'),
    ('"code": "count = 0\\\\nresults = []"}}}}},',
     '"code": "count = 0\\\\nresults = []"}}}},'),
    ('"code": "results.append(result)\\\\ncount += 1"}}}}},',
     '"code": "results.append(result)\\\\ncount += 1"}}}},'),
]

for old, new in fixes:
    if old in content:
        content = content.replace(old, new)
        print(f'Fixed: {old[:60]}...')
    else:
        print(f'NOT FOUND: {old[:60]}...')

with open(r'e:\Flowly-now\Backend\nl_to_workflow\services.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
