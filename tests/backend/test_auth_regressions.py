"""Authentication regressions through real DRF endpoints and JWT validation."""
from datetime import timedelta
from unittest.mock import patch

import jwt
import pytest
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone
from users.authentication import generate_tokens
from users.models import User

pytestmark = pytest.mark.django_db
BASE = '/api/v1/auth/'
PASSWORD = 'Cobalt!48219'


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    from django.core.cache import cache
    cache.clear()


def register_data(**changes):
    return dict(username='regression_user', email='regression@example.invalid',
                password=PASSWORD, password_confirm=PASSWORD, agree_terms=True, **changes)


def test_stale_authorization_does_not_block_login(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION='Bearer expired.invalid.token')
    response = api_client.post(BASE + 'login/', {'username': user.username, 'password': 'testpass123'})
    assert response.status_code == 200


def test_stale_authorization_does_not_block_register(api_client):
    api_client.credentials(HTTP_AUTHORIZATION='Bearer expired.invalid.token')
    assert api_client.post(BASE + 'register/', register_data()).status_code == 201


def test_refresh_token_cannot_access_profile(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + generate_tokens(user)['refresh'])
    assert api_client.get(BASE + 'user/').status_code == 401


def test_disabled_account_cannot_refresh(api_client, user):
    tokens = generate_tokens(user)
    user.is_active = False
    user.save()
    assert api_client.post(BASE + 'refresh/', {'refresh': tokens['refresh']}).status_code == 401


@pytest.mark.parametrize('value', [None, 42, {}, [], 'invalid'])
def test_invalid_refresh_input_never_crashes(api_client, value):
    assert api_client.post(BASE + 'refresh/', {'refresh': value}, format='json').status_code in (400, 401)


def test_signed_malformed_user_id_is_rejected(api_client):
    token = jwt.encode({'user_id': 'invalid', 'type': 'refresh', 'exp': timezone.now() + timedelta(hours=1)}, settings.SECRET_KEY, algorithm='HS256')
    assert api_client.post(BASE + 'refresh/', {'refresh': token}).status_code == 401


def test_email_login_is_case_insensitive(api_client, user):
    assert api_client.post(BASE + 'login/', {'username': user.email.upper(), 'password': 'testpass123'}).status_code == 200


def test_login_error_survives_response_rendering(api_client, user):
    response = api_client.post(BASE + 'login/', {'username': user.username, 'password': 'incorrect'})
    assert response.json()['errors']['non_field_errors'] == ['用户名或密码错误']


def test_legacy_duplicate_email_login_does_not_crash(api_client, user):
    User.objects.create_user(username='duplicate_legacy', email=user.email, password=PASSWORD)
    assert api_client.post(BASE + 'login/', {'username': user.email, 'password': 'testpass123'}).status_code == 401


def test_duplicate_email_registration_is_rejected(api_client, user):
    data = register_data()
    data['email'] = user.email.upper()
    assert api_client.post(BASE + 'register/', data).status_code == 400


def test_registration_requires_email(api_client):
    data = register_data()
    data.pop('email')
    assert api_client.post(BASE + 'register/', data).status_code == 400


def test_password_similarity_uses_account_information(api_client):
    data = register_data()
    data.update(username='aVeryUniqueUser48219', password='aVeryUniqueUser48219', password_confirm='aVeryUniqueUser48219')
    assert api_client.post(BASE + 'register/', data).status_code == 400


def test_logout_revokes_current_session_only(api_client, user):
    current, other = generate_tokens(user), generate_tokens(user)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + current['access'])
    assert api_client.post(BASE + 'logout/').status_code == 200
    assert api_client.get(BASE + 'user/').status_code == 401
    assert api_client.post(BASE + 'refresh/', {'refresh': current['refresh']}).status_code == 401
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + other['access'])
    assert api_client.get(BASE + 'user/').status_code == 200


def test_password_change_revokes_old_tokens_and_preserves_current_session(api_client, user):
    old = generate_tokens(user)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + old['access'])
    response = api_client.post(BASE + 'change-password/', {'old_password': 'testpass123', 'new_password': PASSWORD, 'new_password_confirm': PASSWORD})
    assert response.status_code == 200
    assert api_client.get(BASE + 'user/').status_code == 401
    assert api_client.post(BASE + 'refresh/', {'refresh': old['refresh']}).status_code == 401
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])
    assert api_client.get(BASE + 'user/').status_code == 200


def test_password_reset_and_single_use_link(api_client, user):
    old = generate_tokens(user)
    data = {'uidb64': urlsafe_base64_encode(force_bytes(user.pk)), 'token': default_token_generator.make_token(user), 'new_password': PASSWORD}
    assert api_client.post(BASE + 'password-reset/confirm/', data).status_code == 200
    assert api_client.post(BASE + 'password-reset/confirm/', data).status_code == 400
    assert api_client.post(BASE + 'refresh/', {'refresh': old['refresh']}).status_code == 401
    assert api_client.post(BASE + 'login/', {'username': user.username, 'password': PASSWORD}).status_code == 200


@pytest.mark.parametrize('uid', ['invalid', '%%%%', 'OTk5OTk5OQ'])
def test_invalid_reset_link(api_client, uid):
    assert api_client.post(BASE + 'password-reset/confirm/', {'uidb64': uid, 'token': 'invalid', 'new_password': PASSWORD}).status_code == 400


def test_reset_email_case_insensitive_and_neutral_response(api_client, user, settings):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    response = api_client.post(BASE + 'password-reset/', {'email': user.email.upper()})
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    absent = api_client.post(BASE + 'password-reset/', {'email': 'absent@example.invalid'})
    assert absent.status_code == response.status_code and absent.data == response.data


def test_registration_is_atomic(api_client):
    with patch('users.views.generate_tokens', side_effect=RuntimeError('token issuance failed')):
        assert api_client.post(BASE + 'register/', register_data()).status_code == 500
    assert not User.objects.filter(username='regression_user').exists()


def test_email_shaped_username_can_log_in(api_client, user):
    other = User.objects.create_user(username=user.email, email='separate@example.invalid', password=PASSWORD)
    assert api_client.post(BASE + 'login/', {'username': other.username, 'password': PASSWORD}).status_code == 200


def test_profile_cannot_introduce_ambiguous_email(authenticated_client, user):
    User.objects.create_user(username='another', email='taken@example.invalid', password=PASSWORD)
    assert authenticated_client.patch(BASE + 'user/', {'email': 'TAKEN@example.invalid'}).status_code == 400


def test_reset_mail_failure_is_actionable(api_client, user):
    with patch('users.views.send_mail', side_effect=OSError('mail unavailable')):
        assert api_client.post(BASE + 'password-reset/', {'email': user.email}).status_code == 503


def test_reset_requests_are_throttled(api_client):
    for _ in range(10):
        assert api_client.post(BASE + 'password-reset/', {'email': 'absent@example.invalid'}).status_code == 200
    assert api_client.post(BASE + 'password-reset/', {'email': 'absent@example.invalid'}).status_code == 429
