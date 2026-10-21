"""
URL patterns for users app.
"""

from django.urls import path
from .avatars import UserAvatarView
from .views import (
    RegisterView, LoginView, TokenRefreshView, LogoutView,
    UserProfileView, ChangePasswordView,
    PasswordResetRequestView, PasswordResetConfirmView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('user/', UserProfileView.as_view(), name='user-profile'),
    path('user/avatar/', UserAvatarView.as_view(), name='user-avatar'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
