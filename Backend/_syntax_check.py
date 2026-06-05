import ast
import sys
path = 'e:/Flowly-now/Backend/website_generator/generators/classification.py'
try:
    with open(path, encoding='utf-8') as f:
        source = f.read()
    ast.parse(source)
    print('classification.py: SYNTAX OK')
    sys.exit(0)
except SyntaxError as e:
    print(f'SYNTAX ERROR in classification.py line {e.lineno}: {e.msg}')
    print(f'  Text: {e.text}')
    sys.exit(1)
