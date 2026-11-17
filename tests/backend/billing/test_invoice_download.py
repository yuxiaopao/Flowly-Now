"""Real authenticated statement download, data integrity and escaping."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from billing.models import Invoice
from users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def invoice(user):
    now = timezone.now()
    return Invoice.objects.create(
        user=user, invoice_number='INV-QA-001', subtotal=Decimal('123.45'),
        tax=Decimal('1.55'), discount=Decimal('5'), total=Decimal('120.00'),
        currency='CNY', period_start=now - timedelta(days=30), period_end=now,
        due_date=now + timedelta(days=3), status='paid', paid_at=now,
        line_items=[{'description': '中文应用调用', 'amount': '123.45'}],
    )


def test_owner_downloads_real_statement(authenticated_client, invoice):
    response = authenticated_client.get(f'/api/v1/billing/invoices/{invoice.pk}/download/')
    assert response.status_code == 200
    assert response['Content-Type'].startswith('text/html')
    assert response['Content-Disposition'] == f'attachment; filename="billing-{invoice.pk}.html"'
    content = response.content.decode('utf-8')
    for value in ('INV-QA-001', '120.00', '123.45', '1.55', '5.00', 'CNY', '中文应用调用', '已支付', '非税务发票'):
        assert value in content
    assert response['Cache-Control'] == 'private, no-store'
    assert 'sandbox' in response['Content-Security-Policy']


def test_foreign_user_cannot_download(invoice):
    client = APIClient()
    client.force_authenticate(User.objects.create_user(username='invoice-foreign'))
    assert client.get(f'/api/v1/billing/invoices/{invoice.pk}/download/').status_code == 404


def test_anonymous_cannot_download(invoice):
    assert APIClient().get(f'/api/v1/billing/invoices/{invoice.pk}/download/').status_code in (401, 403)


def test_statement_escapes_untrusted_fields(authenticated_client, invoice):
    invoice.notes = '<script>window.pwned=true</script>'
    invoice.line_items = [{'description': '<img src=x onerror=alert(1)>', 'amount': '120.00'}]
    invoice.save()
    response = authenticated_client.get(f'/api/v1/billing/invoices/{invoice.pk}/download/')
    content = response.content.decode('utf-8')
    assert '<script>' not in content
    assert '<img' not in content
    assert '&lt;script&gt;' in content
    assert '&lt;img' in content


def test_download_does_not_mark_pending_invoice_paid(authenticated_client, invoice):
    invoice.status = 'pending'
    invoice.paid_at = None
    invoice.save()
    response = authenticated_client.get(f'/api/v1/billing/invoices/{invoice.pk}/download/')
    assert response.status_code == 200
    assert '待支付' in response.content.decode('utf-8')
    invoice.refresh_from_db()
    assert invoice.status == 'pending'
    assert invoice.paid_at is None
