"""Real InnoDB concurrency for explicit catalog default changes."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import connection, connections
from rest_framework.test import APIClient

from gateway.models import AIModel, ModelProvider
from users.models import User

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize('same_provider', [True, False])
def test_parallel_admin_default_changes_keep_one_default_per_type(user, same_provider):
    assert connection.vendor == 'mysql', 'Run with config.mysql_test_settings against the isolated MySQL profile.'
    user.is_staff = True
    user.save(update_fields=['is_staff'])
    first_provider = ModelProvider.objects.create(name='First', slug='concurrent-first')
    second_provider = first_provider if same_provider else ModelProvider.objects.create(name='Second', slug='concurrent-second')
    models = [AIModel.objects.create(provider=provider, name=f'Chat {index}', model_id=f'chat-{index}') for index, provider in enumerate([first_provider, second_provider])]
    embedding = AIModel.objects.create(provider=first_provider, name='Embedding', model_id='embedding', model_type='embedding', is_default=True)
    barrier = Barrier(2)

    def change(model_id):
        try:
            client = APIClient()
            client.force_authenticate(User.objects.get(pk=user.pk))
            barrier.wait(timeout=10)
            response = client.post(f'/api/v1/gateway/models/{model_id}/set_default/', {'is_default': True}, format='json')
            return response.status_code, response.data
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        pending = [executor.submit(change, model.pk) for model in models]
        results = [future.result(timeout=30) for future in pending]
    assert [status for status, _ in results] == [200, 200], results
    assert AIModel.objects.filter(model_type='chat', is_active=True, is_default=True).count() == 1
    embedding.refresh_from_db()
    assert embedding.is_default is True
