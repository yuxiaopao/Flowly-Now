#!/usr/bin/env python
"""Ensure CI/local smoke test user exists."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

EMAIL = os.environ.get("FLOWLY_TEST_EMAIL", "nlwftest@flowly.test")
PASSWORD = os.environ.get("FLOWLY_TEST_PASSWORD", "Test123456!")
USERNAME = os.environ.get("FLOWLY_TEST_USERNAME", "nlwftest")


def main():
    user, created = User.objects.get_or_create(
        email=EMAIL,
        defaults={
            "username": USERNAME,
            "is_active": True,
        },
    )
    if created:
        user.set_password(PASSWORD)
        user.save(update_fields=["password"])
        print(f"created test user: {EMAIL}")
        return 0

    changed = False
    if not user.is_active:
        user.is_active = True
        changed = True
    if user.username != USERNAME:
        user.username = USERNAME
        changed = True
    user.set_password(PASSWORD)
    changed = True
    if changed:
        user.save()
    print(f"test user ready: {EMAIL}")

    _ensure_test_tenant(user)

    from django.core.management import call_command

    call_command("seed_demo_data", email=EMAIL)
    return 0


def _ensure_test_tenant(user):
    from tenants.models import Tenant, TenantMembership

    if TenantMembership.objects.filter(user=user, is_active=True).exists():
        return

    slug_base = (user.username or user.email.split("@")[0]).lower().replace("_", "-")
    slug = f"{slug_base}-workspace"
    suffix = 1
    while Tenant.objects.filter(slug=slug).exclude(owner=user).exists():
        suffix += 1
        slug = f"{slug_base}-workspace-{suffix}"

    tenant, _ = Tenant.objects.get_or_create(
        owner=user,
        slug=slug,
        defaults={
            "name": f"{user.username or slug_base} Workspace",
            "billing_email": user.email,
            "status": "active",
            "plan": "free",
            "max_users": 5,
        },
    )
    if tenant.max_users < 5:
        tenant.max_users = 5
        tenant.save(update_fields=["max_users"])
    TenantMembership.objects.get_or_create(
        tenant=tenant,
        user=user,
        defaults={"role": "owner", "is_active": True},
    )
    print(f"test tenant ready: {tenant.slug}")


if __name__ == "__main__":
    sys.exit(main())
