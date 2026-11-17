from django.db import migrations, models

from website_generator.migration_operations import AddFieldIfMissing


class Migration(migrations.Migration):

    dependencies = [
        ('website_generator', '0001_initial'),
    ]

    operations = [
        AddFieldIfMissing(
            model_name='generatedsite',
            name='codegraph_project_id',
            field=models.IntegerField(blank=True, null=True, verbose_name='CodeGraph 项目ID'),
        ),
        AddFieldIfMissing(
            model_name='generatedsite',
            name='show_in_nav',
            field=models.BooleanField(default=True, verbose_name='显示在侧栏导航'),
        ),
    ]
