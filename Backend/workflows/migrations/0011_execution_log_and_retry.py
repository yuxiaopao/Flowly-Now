"""
Migration: Add ExecutionLog model and extend NodeExecution.

- Adds ExecutionLog model for detailed per-node and workflow-level logging
- Adds 'retrying' status to NodeExecution.STATUS_CHOICES
- Adds token_usage JSONField to NodeExecution
- Adds mark_retrying method behavior (no schema change)
"""

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0010_execution_cache'),
    ]

    operations = [
        # ============================================================
        # ExecutionLog model
        # ============================================================
        migrations.CreateModel(
            name='ExecutionLog',
            fields=[
                ('id', models.UUIDField(
                    default=uuid.uuid4,
                    editable=False,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('level', models.CharField(
                    choices=[('DEBUG', 'Debug'), ('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error')],
                    db_index=True,
                    default='INFO',
                    max_length=10,
                    verbose_name='日志级别'
                )),
                ('message', models.TextField(verbose_name='日志消息')),
                ('details', models.JSONField(blank=True, default=dict, verbose_name='详细信息')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='时间戳')),
                ('execution', models.ForeignKey(
                    db_constraint=False,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logs',
                    to='workflows.workflowexecution',
                    verbose_name='执行记录'
                )),
                ('node_execution', models.ForeignKey(
                    blank=True,
                    db_constraint=False,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='logs',
                    to='workflows.nodeexecution',
                    verbose_name='节点执行'
                )),
            ],
            options={
                'verbose_name': '执行日志',
                'verbose_name_plural': '执行日志',
                'db_table': 'execution_logs',
                'ordering': ['timestamp'],
            },
        ),
        # ============================================================
        # Indexes for ExecutionLog
        # ============================================================
        migrations.AddIndex(
            model_name='executionlog',
            index=models.Index(fields=['execution', 'timestamp'], name='execution__exec_id_7dc9a4_idx'),
        ),
        migrations.AddIndex(
            model_name='executionlog',
            index=models.Index(fields=['level'], name='execution__level_4e5e1e_idx'),
        ),
        migrations.AddIndex(
            model_name='executionlog',
            index=models.Index(fields=['node_execution'], name='execution__node_ex_a4d8b3_idx'),
        ),
        # ============================================================
        # Extend NodeExecution: add 'retrying' status choice
        # (No schema change needed for CharField choices)
        # ============================================================
        # ============================================================
        # Extend NodeExecution: add token_usage JSONField
        # ============================================================
        migrations.AddField(
            model_name='nodeexecution',
            name='token_usage',
            field=models.JSONField(blank=True, default=dict, verbose_name='Token使用量'),
        ),
    ]
