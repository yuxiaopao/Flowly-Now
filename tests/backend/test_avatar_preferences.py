"""Animated avatars are the default; images require an explicit user choice."""
import pytest
from users.serializers import AvatarPreferencesSerializer, UserSerializer
from users.constants import AVATAR_MAX_BLOCKS

pytestmark = pytest.mark.django_db
PROFILE_URL = '/api/v1/auth/user/'


def test_dynamic_preferences_round_trip_keeps_the_uploaded_image(authenticated_client, user):
    user.avatar = 'https://example.test/photo.png'
    user.save(update_fields=['avatar'])
    preferences = {'mode': 'robot', 'shape': 'nuage', 'color': 'bleu', 'expression': 'heureux',
                   'blocks': [{'state': 'thinking', 'duration': 2.7}, {'state': 'idle', 'duration': 2.4}]}
    response = authenticated_client.patch(PROFILE_URL, {'avatar_preferences': preferences}, format='json')
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.avatar_preferences == preferences
    assert user.avatar == 'https://example.test/photo.png'
    assert authenticated_client.get(PROFILE_URL).json()['data']['avatar_preferences'] == preferences


def test_switching_image_and_robot_preserves_the_design(authenticated_client, user):
    user.avatar = 'https://example.test/photo.png'
    user.avatar_preferences = {'mode': 'robot', 'shape': 'nuage', 'color': 'bleu'}
    user.save()
    assert authenticated_client.patch(PROFILE_URL, {'avatar_preferences': {'mode': 'image'}}, format='json').status_code == 200
    user.refresh_from_db()
    assert user.avatar_preferences == {'mode': 'image', 'shape': 'nuage', 'color': 'bleu'}
    assert authenticated_client.patch(PROFILE_URL, {'bio': '保留动态头像设计'}, format='json').status_code == 200
    assert authenticated_client.patch(PROFILE_URL, {'avatar_preferences': {'mode': 'robot'}}, format='json').status_code == 200
    user.refresh_from_db()
    assert user.avatar_preferences == {'mode': 'robot', 'shape': 'nuage', 'color': 'bleu'}
    assert user.avatar.endswith('photo.png')


INVALID_PREFERENCES = [None, [], 'robot', {'mode': 'invalid'}, {'shape': 'bad'}, {'color': 'url(javascript:bad)'},
                       {'expression': 'bad'}, {'blocks': 'bad'}, {'blocks': [{'state': 'shell', 'duration': 1}]}]
INVALID_PREFERENCES += [{'blocks': [{'state': 'idle', 'duration': value}]} for value in [0, -1, 11, 'nan', 'inf', 'bad']]
INVALID_PREFERENCES += [{'blocks': [{'state': 'idle', 'duration': 1}] * (AVATAR_MAX_BLOCKS + 1)}]


@pytest.mark.parametrize('preferences', INVALID_PREFERENCES)
def test_invalid_preferences_preserve_the_previous_design(authenticated_client, user, preferences):
    original = {'mode': 'robot', 'shape': 'nuage', 'color': 'bleu'}
    user.avatar_preferences = original
    user.save(update_fields=['avatar_preferences'])
    response = authenticated_client.patch(PROFILE_URL, {'avatar_preferences': preferences}, format='json')
    assert response.status_code == 400
    user.refresh_from_db()
    assert user.avatar_preferences == original


def test_image_mode_requires_an_uploaded_image(authenticated_client, user):
    assert not user.avatar
    response = authenticated_client.patch(PROFILE_URL, {'avatar_preferences': {'mode': 'image'}}, format='json')
    assert response.status_code == 400
    assert '请先上传头像图片' in str(response.data)


def test_new_accounts_expose_empty_preferences_for_the_default_robot(user):
    assert user.avatar_preferences == {}
    assert UserSerializer(user).data['avatar_preferences'] == {}


def test_duration_serializer_rejects_nonfinite_values():
    for duration in ['nan', 'inf', '-inf']:
        serializer = AvatarPreferencesSerializer(data={'blocks': [{'state': 'idle', 'duration': duration}]})
        assert not serializer.is_valid()
