# -*- coding: utf-8 -*-
"""Check API errors"""
import requests
import re

r = requests.get('http://127.0.0.1:8000/api/v1/billing/prices/plans/')
print('Status:', r.status_code)

# Extract KeyError
error_match = re.search(r"KeyError.*?'(\w+)'", r.text)
if error_match:
    print('KeyError:', error_match.group(1))

# Extract OperationalError
op_match = re.search(r"OperationalError.*?:\s*(.+?)(?:\n|$)", r.text)
if op_match:
    print('OperationalError:', op_match.group(1))

# Extract table name
table_match = re.search(r"Table '([^']+)' doesn't exist", r.text)
if table_match:
    print('Missing table:', table_match.group(1))
