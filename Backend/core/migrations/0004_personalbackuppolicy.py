from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('core', '0003_datarestoreoperation'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='PersonalBackupPolicy', fields=[
        ('id', models.BigAutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')),
        ('enabled', models.BooleanField(default=False)),
        ('frequency', models.CharField(max_length=10, default='daily', choices=[('daily', 'daily'), ('weekly', 'weekly'), ('monthly', 'monthly')])),
        ('keep_count', models.PositiveIntegerField(default=7, validators=[MinValueValidator(3), MaxValueValidator(30)])),
        ('next_run_at', models.DateTimeField(null=True, blank=True, db_index=True)),
        ('last_run_at', models.DateTimeField(null=True, blank=True)),
        ('last_error', models.TextField(blank=True)),
        ('updated_at', models.DateTimeField(auto_now=True)),
        ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE, related_name='personal_backup_policy')),
    ])]
