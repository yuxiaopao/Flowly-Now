from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website_generator', '0005_generatedsite_clip_retrieval_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedsite',
            name='agent_memory_enabled',
            field=models.BooleanField(default=True, verbose_name='Agent memory enabled'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='environment_config',
            field=models.JSONField(blank=True, default=dict, verbose_name='Environment config'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='model_artifact_manifest',
            field=models.JSONField(blank=True, default=dict, verbose_name='Model artifact manifest'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='required_features',
            field=models.JSONField(blank=True, default=list, verbose_name='Required features'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='site_brief',
            field=models.JSONField(blank=True, default=dict, verbose_name='Site brief'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='theme_profile',
            field=models.JSONField(blank=True, default=dict, verbose_name='Theme profile'),
        ),
        migrations.AlterField(
            model_name='generatedsite',
            name='status',
            field=models.CharField(choices=[('generating', '生成中'), ('completed', '已完成'), ('failed', '失败'), ('iterating', '迭代中'), ('profiling', 'Profiling'), ('environment_ready', 'Environment ready'), ('backend_ready', 'Backend ready'), ('frontend_ready', 'Frontend ready'), ('ui_polished', 'UI polished'), ('reviewing', 'Reviewing'), ('qa_running', 'QA running'), ('repairing', 'Repairing'), ('preview_ready', 'Preview ready'), ('failed_with_report', 'Failed with report')], default='generating', max_length=20, verbose_name='状态'),
        ),
    ]
