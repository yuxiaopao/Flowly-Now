"""
Tests for Multi-tenancy.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestTenantAPI:
    """Test tenant API endpoints."""

    def test_list_tenants(self, authenticated_client, user):
        """Test listing user's tenants."""
        from tenants.models import Tenant, TenantMembership
        tenant = Tenant.objects.create(
            name='Test Tenant',
            slug='test-tenant',
            owner=user,
            billing_email='test@example.com'
        )
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role='owner'
        )
        response = authenticated_client.get('/api/v1/tenants/tenants/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_tenant(self, authenticated_client):
        """Test creating a new tenant."""
        data = {
            'name': 'New Tenant',
            'slug': 'new-tenant',
            'billing_email': 'billing@example.com'
        }
        response = authenticated_client.post('/api/v1/tenants/tenants/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Tenant'

    def test_tenant_member_added_on_create(self, authenticated_client):
        """Test that owner is added as member on tenant creation."""
        data = {
            'name': 'Tenant with Member',
            'slug': 'tenant-member',
            'billing_email': 'billing@example.com'
        }
        response = authenticated_client.post('/api/v1/tenants/tenants/', data)
        tenant_id = response.data['id']

        from tenants.models import TenantMembership
        membership = TenantMembership.objects.filter(
            tenant_id=tenant_id,
            user=authenticated_client.user
        ).first()
        assert membership is not None
        assert membership.role == 'owner'

    def test_update_tenant_requires_admin(self, authenticated_client, user):
        """Test that only admins can update tenant."""
        from tenants.models import Tenant, TenantMembership
        tenant = Tenant.objects.create(
            name='Admin Test Tenant',
            slug='admin-test',
            owner=user,
            billing_email='test@example.com'
        )
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role='owner'
        )
        data = {'name': 'Updated Name'}
        response = authenticated_client.patch(
            f'/api/v1/tenants/tenants/{tenant.id}/',
            data
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTenantMembership:
    """Test tenant membership endpoints."""

    def test_get_tenant_members(self, authenticated_client, user):
        """Test getting tenant members."""
        from tenants.models import Tenant, TenantMembership
        tenant = Tenant.objects.create(
            name='Members Test',
            slug='members-test',
            owner=user,
            billing_email='test@example.com'
        )
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role='owner'
        )
        response = authenticated_client.get(
            f'/api/v1/tenants/tenants/{tenant.id}/members/'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_invite_member(self, authenticated_client, user):
        """Test inviting a new member."""
        from tenants.models import Tenant, TenantMembership
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Create another user
        new_user = User.objects.create_user(
            username='invited_user',
            email='invited@example.com',
            password='testpass123'
        )

        tenant = Tenant.objects.create(
            name='Invite Test',
            slug='invite-test',
            owner=user,
            billing_email='test@example.com'
        )
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role='owner'
        )

        response = authenticated_client.post(
            f'/api/v1/tenants/tenants/{tenant.id}/invite/',
            {'email': 'invited@example.com', 'role': 'member'}
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTenantInvitation:
    """Test tenant invitation endpoints."""

    def test_accept_invitation(self, authenticated_client, user):
        """Test accepting a tenant invitation."""
        from tenants.models import Tenant, TenantInvitation
        import secrets

        tenant = Tenant.objects.create(
            name='Invitation Test',
            slug='invitation-test',
            owner=user,
            billing_email='test@example.com'
        )

        invitation = TenantInvitation.objects.create(
            tenant=tenant,
            email=user.email,
            role='member',
            invited_by=user,
            token=secrets.token_urlsafe(32),
            expires_at='2027-12-31T23:59:59Z'
        )

        response = authenticated_client.post(
            f'/api/v1/tenants/invitations/{invitation.id}/accept/'
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestTenantUsage:
    """Test tenant usage endpoints."""

    def test_get_tenant_usage(self, authenticated_client, user):
        """Test getting tenant usage statistics."""
        from tenants.models import Tenant, TenantMembership, TenantUsage
        tenant = Tenant.objects.create(
            name='Usage Test',
            slug='usage-test',
            owner=user,
            billing_email='test@example.com'
        )
        TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            role='owner'
        )
        TenantUsage.objects.create(tenant=tenant)

        response = authenticated_client.get(
            f'/api/v1/tenants/tenants/{tenant.id}/usage/'
        )
        assert response.status_code == status.HTTP_200_OK
