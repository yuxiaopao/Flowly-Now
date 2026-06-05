# Generated migration for credential encryption support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0008_domain_nodes_and_templates'),
    ]

    operations = [
        migrations.AddField(
            model_name='apicredential',
            name='is_encrypted',
            field=models.BooleanField(db_index=True, default=True, verbose_name='是否加密'),
        ),
        migrations.AddConstraint(
            model_name='apicredential',
            constraint=models.UniqueConstraint(
                fields=['owner', 'service_type', 'name'],
                name='unique_credential_per_user'
            ),
        ),
    ]
