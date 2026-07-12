from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website_generator', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedsite',
            name='codegraph_project_id',
            field=models.IntegerField(blank=True, null=True, verbose_name='CodeGraph 项目ID'),
        ),
        migrations.AddField(
            model_name='generatedsite',
            name='show_in_nav',
            field=models.BooleanField(default=True, verbose_name='显示在侧栏导航'),
        ),
    ]
