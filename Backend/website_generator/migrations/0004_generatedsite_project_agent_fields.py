from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website_generator', '0003_generatedsite_qa_preview_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generatedsite',
            name='status',
            field=models.CharField(
                choices=[
                    ('generating', '生成中'),
                    ('completed', '已完成'),
                    ('failed', '失败'),
                    ('iterating', '迭代中'),
                ],
                default='generating',
                max_length=20,
                verbose_name='状态',
            ),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='preview_status',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='预览状态'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='rag_collection_id',
            field=models.UUIDField(blank=True, null=True, verbose_name='项目RAG集合ID'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='last_agent_reply',
            field=models.JSONField(blank=True, default=dict, verbose_name='最近Agent回复'),
        ),
    ]
