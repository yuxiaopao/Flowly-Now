from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website_generator', '0004_generatedsite_project_agent_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generatedsite',
            name='website_type',
            field=models.CharField(
                choices=[
                    ('classification', '图像分类'),
                    ('regression', '回归预测'),
                    ('detection', '目标检测'),
                    ('segmentation', '图像分割'),
                    ('nlp_classification', '文本分类'),
                    ('ner', '命名实体识别'),
                    ('clip_retrieval', 'CLIP 检索'),
                ],
                default='classification',
                max_length=50,
                verbose_name='网站类型',
            ),
        ),
    ]
