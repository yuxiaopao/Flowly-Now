"""Initial migration for nl_to_workflow app."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workflows', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NLSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='会话名称')),
                ('description', models.TextField(blank=True, verbose_name='需求描述')),
                ('workflow_name', models.CharField(blank=True, max_length=200, verbose_name='工作流名称')),
                ('workflow_json', models.JSONField(blank=True, default=dict, verbose_name='工作流JSON')),
                ('status', models.CharField(choices=[('active', '进行中'), ('completed', '已完成'), ('failed', '失败')], default='active', max_length=20, verbose_name='状态')),
                ('messages', models.JSONField(default=list, verbose_name='对话历史')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nl_sessions', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
                ('workflow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='nl_sessions', to='workflows.workflow', verbose_name='生成的工作流')),
            ],
            options={
                'verbose_name': 'NL会话',
                'verbose_name_plural': 'NL会话',
                'db_table': 'nl_sessions',
                'ordering': ['-updated_at'],
            },
        ),
    ]
