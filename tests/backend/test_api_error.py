# -*- coding: utf-8 -*-
"""Test API and capture error details"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import requests
import traceback

# Test billing API
print("Testing /api/v1/billing/prices/plans/")
try:
    r = requests.get('http://127.0.0.1:8000/api/v1/billing/prices/plans/')
    print(f"Status: {r.status_code}")
    if r.status_code >= 400:
        print("Error HTML snippet:")
        print(r.text[:2000])
except Exception as e:
    traceback.print_exc()

print("\n" + "="*60)

# Test marketplace API
print("Testing /api/v1/marketplace/templates/")
try:
    r = requests.get('http://127.0.0.1:8000/api/v1/marketplace/templates/')
    print(f"Status: {r.status_code}")
    if r.status_code >= 400:
        print("Error HTML snippet:")
        print(r.text[:2000])
except Exception as e:
    traceback.print_exc()

print("\n" + "="*60)

# Test prompts API
print("Testing /api/v1/prompts/templates/featured/")
try:
    r = requests.get('http://127.0.0.1:8000/api/v1/prompts/templates/featured/')
    print(f"Status: {r.status_code}")
    if r.status_code >= 400:
        print("Error HTML snippet:")
        print(r.text[:2000])
except Exception as e:
    traceback.print_exc()
