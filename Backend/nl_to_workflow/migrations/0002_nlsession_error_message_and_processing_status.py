# Generated migration for nl_to_workflow changes

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workflows', '0001_initial'),
        ('nl_to_workflow', '0001_initial'),
    ]

    operations = [
        # Add error_message field to NLSession
        migrations.AddField(
            model_name='nlsession',
            name='error_message',
            field=models.TextField(blank=True, verbose_name='错误信息'),
        ),

        # Add processing status choice
        migrations.AlterField(
            model_name='nlsession',
            name='status',
            field=models.CharField(
                choices=[
                    ('active', '进行中'),
                    ('processing', '处理中'),
                    ('completed', '已完成'),
                    ('failed', '失败'),
                ],
                default='active',
                max_length=20,
                verbose_name='状态'
            ),
        ),
    ]
