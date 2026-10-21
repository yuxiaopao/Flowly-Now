"""Account profile, password and avatar contract regression tests."""
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from users.avatars import delete_owned_avatar
from users.constants import AVATAR_MAX_BYTES, AVATAR_SIZE
from users.serializers import LoginSerializer, UserCreateSerializer, PasswordResetConfirmSerializer

pytestmark = pytest.mark.django_db
PROFILE_URL = '/api/v1/auth/user/'
AVATAR_URL = f'{PROFILE_URL}avatar/'
PASSWORD_URL = '/api/v1/auth/change-password/'


def image_file(image_format='PNG', size=(512, 384)):
    output = BytesIO()
    Image.new('RGB', size, 'blue').save(output, format=image_format)
    return SimpleUploadedFile('avatar.png', output.getvalue(), content_type='image/png')


def payload(response):
    return response.data.get('data') or response.data


@pytest.fixture(autouse=True)
def temporary_media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def test_profile_round_trip_and_read_only_permissions(authenticated_client, user):
    response = authenticated_client.patch(PROFILE_URL, {
        'first_name': '小流', 'last_name': '陈', 'bio': '研发' * 250,
        'phone': '+86 13800000000', 'role': 'admin', 'is_staff': True,
    }, format='json')
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == '小流'
    assert len(user.bio) == 500
    assert user.role == 'user' and not user.is_staff
    assert payload(authenticated_client.get(PROFILE_URL))['last_name'] == '陈'


@pytest.mark.parametrize('data', [{'email': 'invalid'}, {'username': 'bad name'}, {'bio': 'a' * 501}])
def test_profile_rejects_invalid_values(authenticated_client, data):
    assert authenticated_client.patch(PROFILE_URL, data, format='json').status_code == 400


def test_avatar_upload_resize_replace_and_delete(authenticated_client, user, settings, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = authenticated_client.post(AVATAR_URL, {'avatar': image_file()}, format='multipart')
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.avatar == payload(response)['avatar']
    files = list(Path(settings.MEDIA_ROOT).rglob('*.png'))
    assert len(files) == 1
    with Image.open(files[0]) as image:
        assert image.format == 'PNG'
        assert image.width <= AVATAR_SIZE[0] and image.height <= AVATAR_SIZE[1]
    with django_capture_on_commit_callbacks(execute=True):
        assert authenticated_client.post(AVATAR_URL, {'avatar': image_file('JPEG')}, format='multipart').status_code == 200
    assert not files[0].exists()
    assert len(list(Path(settings.MEDIA_ROOT).rglob('*.png'))) == 1
    with django_capture_on_commit_callbacks(execute=True):
        assert authenticated_client.delete(AVATAR_URL).status_code == 200
    user.refresh_from_db()
    assert user.avatar == ''
    assert not list(Path(settings.MEDIA_ROOT).rglob('*.png'))


@pytest.mark.parametrize('file', [
    SimpleUploadedFile('bad.png', b'not an image', content_type='image/png'),
    SimpleUploadedFile('large.png', b'a' * (AVATAR_MAX_BYTES + 1), content_type='image/png'),
])
def test_invalid_avatar_preserves_existing(authenticated_client, user, file):
    user.avatar = 'https://example.com/original.png'
    user.save(update_fields=['avatar'])
    assert authenticated_client.post(AVATAR_URL, {'avatar': file}, format='multipart').status_code == 400
    user.refresh_from_db()
    assert user.avatar == 'https://example.com/original.png'


def test_avatar_rejects_unsupported_image_and_missing_file(authenticated_client):
    assert authenticated_client.post(AVATAR_URL, {'avatar': image_file('GIF')}, format='multipart').status_code == 400
    assert authenticated_client.post(AVATAR_URL, {}, format='multipart').status_code == 400


def test_avatar_cannot_delete_another_users_file(user):
    path = f'avatars/{user.pk + 1}/' + 'a' * 32 + '.png'
    default_storage.save(path, image_file())
    delete_owned_avatar(default_storage.url(path), user.pk)
    assert default_storage.exists(path)


def test_unauthenticated_account_changes_denied(api_client):
    for response in [api_client.patch(PROFILE_URL, {}), api_client.post(AVATAR_URL, {}), api_client.delete(AVATAR_URL), api_client.post(PASSWORD_URL, {})]:
        assert response.status_code in (401, 403)


def test_password_success_preserves_whitespace(authenticated_client, user):
    user.set_password(' Current-Vx9! ')
    user.save()
    response = authenticated_client.post(PASSWORD_URL, {
        'old_password': ' Current-Vx9! ', 'new_password': ' New-Jk83! ', 'new_password_confirm': ' New-Jk83! ',
    }, format='json')
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.check_password(' New-Jk83! ')
    assert not user.check_password('New-Jk83!')
    assert LoginSerializer(data={'username': user.username, 'password': ' New-Jk83! '}).is_valid()
    assert not LoginSerializer(data={'username': user.username, 'password': 'New-Jk83!'}).is_valid()


@pytest.mark.parametrize('old,new,confirm,field', [
    ('wrong', 'Uncommon-8x#', 'Uncommon-8x#', 'old_password'),
    ('testpass123', 'Uncommon-8x#', 'different', 'new_password_confirm'),
    ('testpass123', '12345678', '12345678', 'new_password'),
])
def test_password_errors_leave_original_password(authenticated_client, user, old, new, confirm, field):
    response = authenticated_client.post(PASSWORD_URL, {'old_password': old, 'new_password': new, 'new_password_confirm': confirm}, format='json')
    assert response.status_code == 400
    assert field in response.data['errors']
    user.refresh_from_db()
    assert user.check_password('testpass123')


def test_registration_preserves_password_whitespace():
    serializer = UserCreateSerializer(data={
        'username': 'whitespace_user', 'email': 'space@example.test',
        'password': ' Spaced-7jQ! ', 'password_confirm': ' Spaced-7jQ! ',
    })
    assert serializer.is_valid(), serializer.errors
    user = serializer.save()
    assert user.check_password(' Spaced-7jQ! ')
    assert LoginSerializer(data={'username': user.username, 'password': ' Spaced-7jQ! '}).is_valid()


def test_reset_preserves_password_whitespace():
    serializer = PasswordResetConfirmSerializer(data={'uidb64': 'MQ', 'token': 'reset-token', 'new_password': ' Reset-7jQ! '})
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data['new_password'] == ' Reset-7jQ! '
