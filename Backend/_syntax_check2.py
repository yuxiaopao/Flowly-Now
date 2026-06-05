import ast
import sys
import os

files = [
    'e:/Flowly-now/Backend/website_generator/generators/__init__.py',
    'e:/Flowly-now/Backend/website_generator/generators/detection.py',
    'e:/Flowly-now/Backend/website_generator/generators/nlp.py',
    'e:/Flowly-now/Backend/website_generator/generators/regression.py',
    'e:/Flowly-now/Backend/website_generator/generators/base.py',
    'e:/Flowly-now/Backend/website_generator/__init__.py',
    'e:/Flowly-now/Backend/website_generator/apps.py',
    'e:/Flowly-now/Backend/website_generator/models.py',
    'e:/Flowly-now/Backend/website_generator/serializers.py',
    'e:/Flowly-now/Backend/website_generator/views.py',
    'e:/Flowly-now/Backend/website_generator/urls.py',
]

for path in files:
    try:
        with open(path, encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        print(f'OK: {os.path.basename(path)}')
    except SyntaxError as e:
        print(f'ERROR in {os.path.basename(path)} line {e.lineno}: {e.msg}')
        print(f'  Text: {e.text}')
    except Exception as e:
        print(f'ERROR in {os.path.basename(path)}: {e}')
