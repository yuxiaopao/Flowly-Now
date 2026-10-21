from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('users', '0002_alter_user_groups')]
    operations = [migrations.CreateModel(
        name='RevokedSession',
        fields=[
            ('session_id', models.CharField(max_length=36, primary_key=True, serialize=False)),
            ('expires_at', models.DateTimeField(db_index=True)),
        ],
    )]
