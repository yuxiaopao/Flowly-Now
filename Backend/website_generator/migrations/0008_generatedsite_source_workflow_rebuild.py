from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('website_generator', '0007_rename_generated_s_status_8d0f0d_idx_generated_s_status_1e4822_idx_and_more'),
        ('workflows', '0020_workflow_is_release_snapshot'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name='generatedsite', name='source_recorded', field=models.BooleanField(default=False, editable=False)),
        migrations.AddField(model_name='generatedsite', name='source_workflow', field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_sites', to='workflows.workflow')),
        migrations.AddField(model_name='generatedsite', name='source_node', field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_sites', to='workflows.node')),
        migrations.AddField(model_name='generatedsite', name='source_execution', field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_sites', to='workflows.workflowexecution')),
        migrations.CreateModel(name='SiteWorkflowRebuild', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('key_hash', models.CharField(max_length=64)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('site', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_rebuilds', to='website_generator.generatedsite')),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ('workflow', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='workflows.workflow')),
        ], options={'constraints': [models.UniqueConstraint(fields=('site', 'user', 'key_hash'), name='site_workflow_rebuild_unique')]}),
    ]
