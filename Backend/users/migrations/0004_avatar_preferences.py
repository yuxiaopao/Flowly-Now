from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0003_revokedsession')]
    operations = [migrations.AddField(
        model_name='user',
        name='avatar_preferences',
        field=models.JSONField(default=dict, blank=True, verbose_name='动态头像设置'),
    )]
