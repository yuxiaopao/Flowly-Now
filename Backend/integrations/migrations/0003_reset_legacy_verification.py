"""Old connect endpoints did not verify credentials. Preserve data, reset the claim."""
import json

from django.db import migrations


def migrate_legacy(apps, schema_editor):
    from workflows.services.encryption_utils import encrypt_value
    Integration = apps.get_model('integrations', 'Integration')
    public_keys = {'events', 'keyword', 'chat_id', 'range', 'spreadsheet_id'}
    secret_keys = {'webhook_url', 'token', 'secret'}
    for item in Integration.objects.using(schema_editor.connection.alias).all().iterator():
        old_config = item.config if isinstance(item.config, dict) else {}
        old_secrets = item.credentials if isinstance(item.credentials, dict) else {}
        if 'encrypted' in old_secrets:
            continue
        values = {**old_config, **old_secrets}
        if item.integration_type == 'custom' and 'slack' in item.name.lower():
            item.integration_type = 'slack'
        if values.get('url') and not values.get('webhook_url'):
            values['webhook_url'] = values['url']
        secrets = {key: value for key, value in values.items() if key in secret_keys}
        item.config = {key: value for key, value in old_config.items() if key in public_keys}
        item.credentials = {
            'encrypted': encrypt_value(json.dumps(secrets)),
            'legacy_encrypted': encrypt_value(json.dumps({'config': old_config, 'credentials': old_secrets})),
        }
        item.is_connected = False
        item.verification_status = 'untested'
        item.save(update_fields=['integration_type', 'config', 'credentials', 'is_connected', 'verification_status'])


class Migration(migrations.Migration):
    dependencies = [('integrations', '0002_integration_last_checked_at_integration_last_error_and_more')]
    operations = [migrations.RunPython(migrate_legacy, migrations.RunPython.noop)]
