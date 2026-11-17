import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('core', '0002_personal_export_snapshots'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='DataRestoreOperation', fields=[
        ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
        ('snapshot_digest', models.CharField(max_length=64)),
        ('expires_at', models.DateTimeField()),
        ('result', models.JSONField(null=True, blank=True)),
        ('completed_at', models.DateTimeField(null=True, blank=True)),
        ('created_at', models.DateTimeField(auto_now_add=True)),
        ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE, related_name='data_restores')),
        ('export', models.ForeignKey(to='core.dataexport', on_delete=django.db.models.deletion.CASCADE, related_name='restores')),
    ])]
