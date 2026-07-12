from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0003_rename_training_dat_tenant_idx_training_da_tenant__3e63b3_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingjob',
            name='training_kind',
            field=models.CharField(
                choices=[
                    ('generic', '通用训练'),
                    ('yolo', 'YOLO训练'),
                    ('clip_cls', 'CLIP分类'),
                    ('clip_ret', 'CLIP检索'),
                ],
                db_index=True,
                default='generic',
                max_length=20,
                verbose_name='训练类型',
            ),
        ),
    ]
