"""
Add error handling fields to Node model and extend WorkflowExecution.

Revision ID: 0002_add_error_handling
Revises: 0001_initial
Create Date: 2026-05-09
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0001_initial'),
    ]

    operations = [
        # Node error handling fields
        migrations.AddField(
            model_name='node',
            name='error_handling',
            field=models.CharField(
                choices=[
                    ('stop', '停止'),
                    ('skip', '跳过'),
                    ('retry', '重试'),
                    ('fallback', '备用值'),
                ],
                default='stop',
                max_length=20,
                verbose_name='错误处理策略'
            ),
        ),
        migrations.AddField(
            model_name='node',
            name='max_retries',
            field=models.IntegerField(default=3, verbose_name='最大重试次数'),
        ),
        migrations.AddField(
            model_name='node',
            name='retry_delay',
            field=models.FloatField(default=1.0, verbose_name='重试延迟(秒)'),
        ),
        migrations.AddField(
            model_name='node',
            name='fallback_value',
            field=models.JSONField(
                blank=True,
                null=True,
                verbose_name='备用值'
            ),
        ),
        # WorkflowExecution new fields
        migrations.AddField(
            model_name='workflowexecution',
            name='version',
            field=models.IntegerField(default=1, verbose_name='工作流版本'),
        ),
        migrations.AddField(
            model_name='workflowexecution',
            name='execution_logs',
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name='执行日志'
            ),
        ),
        migrations.AddField(
            model_name='workflowexecution',
            name='paused_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='暂停时间'
            ),
        ),
        migrations.AddField(
            model_name='workflowexecution',
            name='progress',
            field=models.IntegerField(default=0, verbose_name='进度百分比'),
        ),
        migrations.AddField(
            model_name='workflowexecution',
            name='current_node_id',
            field=models.IntegerField(
                blank=True,
                null=True,
                verbose_name='当前执行节点ID'
            ),
        ),
        migrations.AddField(
            model_name='workflowexecution',
            name='context_snapshot',
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name='上下文快照'
            ),
        ),
        migrations.AddField(
            model_name='workflowexecution',
            name='trigger_source',
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name='触发源信息'
            ),
        ),
        # Add paused status choice
        migrations.AlterField(
            model_name='workflowexecution',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', '等待中'),
                    ('running', '运行中'),
                    ('paused', '已暂停'),
                    ('completed', '已完成'),
                    ('failed', '失败'),
                    ('cancelled', '已取消'),
                ],
                default='pending',
                max_length=20,
                verbose_name='状态'
            ),
        ),
        # Add index for triggered_by
        migrations.AddIndex(
            model_name='workflowexecution',
            index=models.Index(
                fields=['triggered_by', '-started_at'],
                name='workflow_wf_trigger_idx'
            ),
        ),
    ]
