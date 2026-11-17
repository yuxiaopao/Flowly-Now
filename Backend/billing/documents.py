"""Self-contained, printable statements from persisted invoice data."""
import json

from django.http import HttpResponse
from django.template.loader import render_to_string


def invoice_statement_response(invoice):
    content = render_to_string('billing/statement.html', {
        'invoice': invoice,
        'line_items_json': json.dumps(invoice.line_items, ensure_ascii=False, indent=2),
    })
    response = HttpResponse(content, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="billing-{invoice.pk}.html"'
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response
