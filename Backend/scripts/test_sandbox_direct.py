import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from workflows.services.sandbox_service import SandboxService

s = SandboxService()
print("docker available:", s._docker_available)
code = "output = {'sum': 1 + 2}"
r = s.execute(code, {"input": {}})
print("success:", r.success)
print("error:", r.error)
print("output:", r.output)
