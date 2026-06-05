"""
Billing API URL Configuration.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PriceTierViewSet, SubscriptionViewSet, UsageRecordViewSet,
    InvoiceViewSet, PaymentViewSet, CouponViewSet
)

router = DefaultRouter()
router.register(r'prices', PriceTierViewSet, basename='price-tier')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'usage', UsageRecordViewSet, basename='usage-record')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'coupons', CouponViewSet, basename='coupon')

urlpatterns = [
    path('', include(router.urls)),
]
