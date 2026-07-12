from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='format',
            field=models.CharField(
                choices=[
                    ('text', 'TXT'),
                    ('csv', 'CSV'),
                    ('json', 'JSON'),
                    ('parquet', 'Parquet'),
                    ('yolo', 'YOLO'),
                    ('image_folder', 'Image Folder'),
                    ('image_text_pairs', 'Image-Text Pairs'),
                    ('classification_folders', 'Classification Folders'),
                ],
                default='csv',
                max_length=32,
                verbose_name='数据格式',
            ),
        ),
    ]
