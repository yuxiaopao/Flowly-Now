"""
URL patterns for tenants app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantViewSet, TenantMembershipViewSet,
    TenantInvitationViewSet, TenantUsageViewSet,
    TeamSkillViewSet, TeamTaskViewSet, TeamActivityViewSet
)

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'memberships', TenantMembershipViewSet, basename='membership')
router.register(r'invitations', TenantInvitationViewSet, basename='invitation')
router.register(r'usage', TenantUsageViewSet, basename='usage')
router.register(r'skills', TeamSkillViewSet, basename='teamskill')
router.register(r'tasks', TeamTaskViewSet, basename='teamtask')
router.register(r'activities', TeamActivityViewSet, basename='teamactivity')

urlpatterns = [
    path('', include(router.urls)),
]
