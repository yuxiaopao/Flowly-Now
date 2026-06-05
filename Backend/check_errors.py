# -*- coding: utf-8 -*-
"""Check API errors"""
import requests

# Test each failing endpoint
endpoints = [
    '/api/v1/billing/prices/plans/',
    '/api/v1/marketplace/templates/',
    '/api/v1/marketplace/categories/',
    '/api/v1/integrations/templates/available/',
    '/api/v1/workflows/templates/',
    '/api/v1/prompts/templates/featured/',
]

for endpoint in endpoints:
    r = requests.get('http://127.0.0.1:8000' + endpoint)
    print('=' * 60)
    print('Endpoint:', endpoint)
    print('Status:', r.status_code)

    # Print first 1000 chars of response
    if r.status_code >= 400:
        content = r.text
        # Find the main error message
        import re
        # Look for Django debug info
        title_match = re.search(r'<title>([^<]+)</title>', content)
        if title_match:
            print('Title:', title_match.group(1))

        # Look for the actual exception
        exc_match = re.search(r'>([^<]*Error[^<]*)<', content)
        if exc_match:
            print('Exception:', exc_match.group(1))

        # Print a snippet of the content
        print('Content preview:', content[:500])
        print()
