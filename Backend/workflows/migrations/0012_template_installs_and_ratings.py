"""
Migration: Add TemplateInstall, TemplateRatingRecord, TemplateReport models
and is_public / report_count fields.

- Adds TemplateInstall for canonical template installation records
- Adds TemplateRatingRecord for canonical user ratings
- Adds TemplateReport for canonical template reports
- Adds is_public and report_count to WorkflowTemplate
"""

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency('auth.User'),
        ('workflows', '0011_execution_log_and_retry'),
    ]

    operations = [
        # ============================================================
        # TemplateInstall — canonical installation tracking
        # ============================================================
        migrations.CreateModel(
            name='TemplateInstall',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('installed_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='template_installs', to='auth.User')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='installs', to='workflows.workflowtemplate')),
                ('workflow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='template_install', to='workflows.workflow')),
            ],
            options={'db_table': 'workflows_template_installs', 'unique_together': {('user', 'template')}, 'ordering': ['-installed_at']},
        ),
        migrations.AddIndex(model_name='templateinstall', index=models.Index(fields=['template', '-installed_at'], name='wf_tmpl_ins_template_idx')),
        migrations.AddIndex(model_name='templateinstall', index=models.Index(fields=['user', '-installed_at'], name='wf_tmpl_ins_user_idx')),

        # ============================================================
        # TemplateRatingRecord — canonical rating tracking
        # ============================================================
        migrations.CreateModel(
            name='TemplateRatingRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('rating', models.PositiveSmallIntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='template_ratings', to='auth.User')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rating_records', to='workflows.workflowtemplate')),
            ],
            options={'db_table': 'workflows_template_ratings', 'unique_together': {('user', 'template')}, 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(model_name='templateratingrecord', index=models.Index(fields=['template', '-rating'], name='wf_tmpl_rat_template_idx')),
        migrations.AddIndex(model_name='templateratingrecord', index=models.Index(fields=['user'], name='wf_tmpl_rat_user_idx')),

        # ============================================================
        # TemplateReport — canonical report tracking
        # ============================================================
        migrations.CreateModel(
            name='TemplateReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('reason', models.CharField(choices=[
                    ('inappropriate', '不当内容'),
                    ('spam', '垃圾信息'),
                    ('copyright', '侵权内容'),
                    ('misleading', '误导性内容'),
                    ('broken', '内容损坏/不可用'),
                    ('other', '其他'),
                ], max_length=20)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[
                    ('pending', '待处理'),
                    ('reviewed', '已审核'),
                    ('resolved', '已处理'),
                    ('dismissed', '已驳回'),
                ], default='pending', max_length=20)),
                ('reviewed_at', models.DateTimeField(null=True, blank=True)),
                ('reviewed_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='template_reports', to='auth.User')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='workflows.workflowtemplate')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_template_reports', to='auth.User')),
            ],
            options={'db_table': 'workflows_template_reports', 'unique_together': {('user', 'template', 'reason')}, 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(model_name='templatereport', index=models.Index(fields=['template', '-created_at'], name='wf_tmpl_rep_template_idx')),
        migrations.AddIndex(model_name='templatereport', index=models.Index(fields=['status', '-created_at'], name='wf_tmpl_rep_status_idx')),
        migrations.AddIndex(model_name='templatereport', index=models.Index(fields=['user'], name='wf_tmpl_rep_user_idx')),

        # ============================================================
        # WorkflowTemplate extensions
        # ============================================================
        migrations.AddField(model_name='workflowtemplate', name='is_public', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='workflowtemplate', name='report_count', field=models.IntegerField(default=0)),
    ]
