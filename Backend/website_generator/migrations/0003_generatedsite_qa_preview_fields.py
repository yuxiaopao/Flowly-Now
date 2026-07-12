from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website_generator', '0002_generatedsite_nav_codegraph'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedsite',
            name='last_qa_gate',
            field=models.CharField(blank=True, max_length=20, verbose_name='最近QA档位'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='last_qa_report',
            field=models.JSONField(blank=True, default=dict, verbose_name='最近QA报告'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='last_preview_url',
            field=models.CharField(blank=True, max_length=500, verbose_name='最近预览URL'),
        ),
    ]
