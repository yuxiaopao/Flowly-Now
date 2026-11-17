"""The dataset HTTP surface never exposes another account's personal upload."""
from pathlib import Path
import pytest
from django.core.files.base import ContentFile
from rest_framework.test import APIClient
from datasets.models import Dataset

pytestmark = pytest.mark.django_db
BASE = '/api/v1/datasets/'


def uploaded(owner, name):
    row = Dataset.objects.create(created_by=owner, name=name, source='upload', format='csv', status='ready',
        row_count=1, columns=['value', 'label'], preview_data=[{'value': 1, 'label': name}])
    row.file.save(name + '.csv', ContentFile(b'value,label\n1,fixture\n'))
    return row


def test_personal_list_detail_preview_download_update_and_delete_are_owner_scoped(user, admin_user, authenticated_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    own = uploaded(user, 'Own upload')
    foreign = uploaded(admin_user, 'Private foreign upload')
    listing = authenticated_client.get(BASE)
    assert listing.status_code == 200
    assert {entry['id'] for entry in listing.data['data']['results']} == {str(own.pk)}
    url = f'{BASE}{foreign.pk}/'
    for suffix in ('', 'preview/', 'stats/', 'download/'):
        assert authenticated_client.get(url + suffix).status_code == 404
    assert authenticated_client.patch(url, {'name': 'Taken'}, format='multipart').status_code == 404
    assert authenticated_client.post(url + 'reprocess/', {}, format='multipart').status_code == 404
    assert authenticated_client.delete(url).status_code == 404
    foreign.refresh_from_db()
    assert foreign.name == 'Private foreign upload' and Path(foreign.file.path).is_file()
    own_url = f'{BASE}{own.pk}/'
    assert authenticated_client.get(own_url).status_code == authenticated_client.get(own_url + 'preview/').status_code == 200
    download = authenticated_client.get(own_url + 'download/')
    assert download.status_code == 200 and b'fixture' in b''.join(download.streaming_content)
    download.close()
    own_file = Path(own.file.path)
    assert authenticated_client.delete(own_url).status_code == 204
    assert not own_file.exists() and Dataset.objects.filter(pk=foreign.pk).exists()


def test_active_team_sharing_and_superuser_access_are_preserved(user, admin_user, authenticated_client, settings, tmp_path):
    from tenants.models import Tenant, TenantMembership
    settings.MEDIA_ROOT = tmp_path
    shared_team = Tenant.objects.create(owner=admin_user, name='Shared team', slug='shared-datasets')
    other_team = Tenant.objects.create(owner=admin_user, name='Other team', slug='other-datasets')
    membership = TenantMembership.objects.create(tenant=shared_team, user=user, role='member', is_active=True)
    shared = uploaded(admin_user, 'Shared upload')
    shared.tenant = shared_team
    shared.save(update_fields=['tenant'])
    hidden = uploaded(admin_user, 'Other team upload')
    hidden.tenant = other_team
    hidden.save(update_fields=['tenant'])
    assert authenticated_client.get(f'{BASE}{shared.pk}/').status_code == 200
    assert authenticated_client.get(f'{BASE}{hidden.pk}/').status_code == 404
    membership.is_active = False
    membership.save(update_fields=['is_active'])
    assert authenticated_client.get(f'{BASE}{shared.pk}/').status_code == 404
    administrator = APIClient()
    administrator.force_authenticate(admin_user)
    assert administrator.get(f'{BASE}{shared.pk}/').status_code == 200
    assert administrator.get(f'{BASE}{hidden.pk}/').status_code == 200
