from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='dataexport', name='snapshot',
            field=models.JSONField(default=dict, blank=True, editable=False, verbose_name='导出快照'),
        ),
        migrations.AddField(
            model_name='dataexport', name='is_backup',
            field=models.BooleanField(default=False, db_index=True, editable=False, verbose_name='自动备份'),
        ),
        migrations.AlterField(
            model_name='dataexport', name='export_type',
            field=models.CharField(max_length=30, verbose_name='导出类型', choices=[
                ('full', '全量导出'), ('workflows', '工作流导出'), ('agents', 'Agent导出'),
                ('executions', '执行记录导出'), ('usage', '使用记录导出'), ('audit_logs', '审计日志导出'),
            ]),
        ),
    ]
