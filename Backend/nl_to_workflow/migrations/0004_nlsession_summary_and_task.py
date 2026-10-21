# Generated manually for NL intelligence P2

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nl_to_workflow', '0003_auto_20260513_1418'),
    ]

    operations = [
        migrations.AddField(
            model_name='nlsession',
            name='conversation_summary',
            field=models.TextField(blank=True, default='', verbose_name='对话摘要'),
        ),
        migrations.AddField(
            model_name='nlsession',
            name='celery_task_id',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='Celery任务ID'),
        ),
    ]
