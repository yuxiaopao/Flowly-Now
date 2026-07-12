"""Debug NL provider registration."""
import os
import sys
import django
sys.path.insert(0, r'e:\Flowly-now\Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from gateway.providers.registry import get_registry, register_default_providers, default_registry

print("=== Registry State ===")
print(f"OLLAMA_BASE_URL from settings: {getattr(settings, 'OLLAMA_BASE_URL', 'NOT SET')}")
print(f"OLLAMA_BASE_URL from .env: {os.getenv('OLLAMA_BASE_URL', 'NOT SET')}")
print(f"default_registry.get_all(): {default_registry.get_all()}")

print("\n=== Registering providers ===")
register_default_providers()
print(f"After register: {default_registry.get_all()}")

print("\n=== Listing models ===")
models = default_registry.list_models()
print(f"Models: {len(models)}")
for m in models:
    print(f"  - {m.model_id} ({m.provider})")

print("\n=== Ollama direct test ===")
import requests
try:
    resp = requests.get('http://localhost:11434/api/tags', timeout=5)
    print(f"  Ollama /api/tags: {resp.status_code}")
    data = resp.json()
    print(f"  Models: {[m['name'] for m in data.get('models', [])]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== NLToWorkflowService test ===")
from nl_to_workflow.services import NLToWorkflowService
svc = NLToWorkflowService()
print(f"  registry.get_all(): {svc.registry.get_all()}")
print(f"  registry.list_models(): {len(svc.registry.list_models())}")
for m in svc.registry.list_models():
    print(f"    - {m.model_id}")
print(f"  resolved model: {svc._resolve_model()}")
print(f"  llm: {svc.llm}")
