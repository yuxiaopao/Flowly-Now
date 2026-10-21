"""
Tests for User authentication.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestUserRegistration:
    """Test user registration."""

    @pytest.mark.parametrize('consent', [False, 'false', '0', 0])
    def test_registration_requires_explicit_terms_acceptance(self, api_client, consent):
        from users.models import User
        response = api_client.post('/api/v1/auth/register/', {
            'username': 'consentuser', 'email': 'consent@example.com',
            'password': 'securepass123', 'password_confirm': 'securepass123',
            'agree_terms': consent,
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.filter(username='consentuser').exists()

    def test_register_user(self, api_client):
        """Test user registration."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password_confirm': 'securepass123',
            'agree_terms': True,
        }
        response = api_client.post('/api/v1/auth/register/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['user']['username'] == 'newuser'

    def test_register_password_mismatch(self, api_client):
        """Test registration with mismatched passwords."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123',
            'password_confirm': 'differentpass',
            'agree_terms': True,
        }
        response = api_client.post('/api/v1/auth/register/', data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Test user login."""

    def test_login_success(self, api_client, user):
        """Test successful login."""
        data = {
            'username': user.username,
            'password': 'testpass123'
        }
        response = api_client.post('/api/v1/auth/login/', data)
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_login_wrong_password(self, api_client, user):
        """Test login with wrong password."""
        data = {
            'username': user.username,
            'password': 'wrongpassword'
        }
        response = api_client.post('/api/v1/auth/login/', data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login with nonexistent user."""
        data = {
            'username': 'nonexistent',
            'password': 'somepassword'
        }
        response = api_client.post('/api/v1/auth/login/', data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefresh:
    """Test token refresh."""

    def test_refresh_token(self, api_client, user):
        """Test refreshing access token."""
        # First login
        login_response = api_client.post('/api/v1/auth/login/', {
            'username': user.username,
            'password': 'testpass123'
        })
        refresh_token = login_response.data['refresh']

        # Refresh token
        response = api_client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token
        })
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data


@pytest.mark.django_db
class TestUserProfile:
    """Test user profile endpoints."""

    def test_get_profile(self, authenticated_client):
        """Test getting user profile."""
        response = authenticated_client.get('/api/v1/auth/user/')
        assert response.status_code == status.HTTP_200_OK

    def test_update_profile(self, authenticated_client):
        """Test updating user profile."""
        data = {
            'first_name': 'Test',
            'last_name': 'User',
            'bio': 'Updated bio'
        }
        response = authenticated_client.patch('/api/v1/auth/user/', data)
        assert response.status_code == status.HTTP_200_OK

    def test_change_password(self, authenticated_client):
        """Test changing password."""
        data = {
            'old_password': 'testpass123',
            'new_password': 'newsecurepass123',
            'new_password_confirm': 'newsecurepass123'
        }
        response = authenticated_client.post('/api/v1/auth/change-password/', data)
        assert response.status_code == status.HTTP_200_OK
