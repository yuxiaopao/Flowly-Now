import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('applications', '0003_applicationrelease_workflow_manifest_and_more')]

    operations = [migrations.AddField(
        model_name='applicationrelease', name='validated_by_request',
        field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                related_name='validated_releases', to='applications.applicationrequest'),
    )]
