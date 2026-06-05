# Generated migration for monitoring app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workflows', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExecutionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_id', models.CharField(blank=True, max_length=100, verbose_name='节点ID')),
                ('node_name', models.CharField(blank=True, max_length=200, verbose_name='节点名称')),
                ('level', models.CharField(choices=[('debug', '调试'), ('info', '信息'), ('warning', '警告'), ('error', '错误')], default='info', max_length=20, verbose_name='日志级别')),
                ('message', models.TextField(verbose_name='日志消息')),
                ('details', models.JSONField(blank=True, default=dict, verbose_name='详细信息')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='时间戳')),
                ('workflow_execution', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='monitoring_logs',
                    to='workflows.workflowexecution',
                    verbose_name='工作流执行'
                )),
            ],
            options={
                'verbose_name': '执行日志',
                'verbose_name_plural': '执行日志',
                'db_table': 'monitoring_execution_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='AlertRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='规则名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('condition', models.CharField(choices=[('execution_failed', '执行失败'), ('execution_timeout', '执行超时'), ('error_rate_high', '错误率高'), ('execution_duration_high', '执行时间过长'), ('api_quota_exceeded', 'API配额超限'), ('user_quota_exceeded', '用户配额超限')], max_length=50, verbose_name='触发条件')),
                ('severity', models.CharField(choices=[('low', '低'), ('medium', '中'), ('high', '高'), ('critical', '严重')], default='medium', max_length=20, verbose_name='严重程度')),
                ('threshold', models.IntegerField(default=1, verbose_name='阈值')),
                ('time_window_minutes', models.IntegerField(default=5, verbose_name='时间窗口(分钟)')),
                ('notify_email', models.BooleanField(default=True, verbose_name='邮件通知')),
                ('notify_webhook', models.BooleanField(default=False, verbose_name='Webhook通知')),
                ('webhook_url', models.URLField(blank=True, max_length=500, verbose_name='Webhook URL')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='alert_rules', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
            ],
            options={
                'verbose_name': '告警规则',
                'verbose_name_plural': '告警规则',
                'db_table': 'monitoring_alert_rules',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('severity', models.CharField(choices=[('low', '低'), ('medium', '中'), ('high', '高'), ('critical', '严重')], max_length=20, verbose_name='严重程度')),
                ('title', models.CharField(max_length=200, verbose_name='告警标题')),
                ('message', models.TextField(verbose_name='告警消息')),
                ('triggered_by_type', models.CharField(blank=True, max_length=50, verbose_name='触发对象类型')),
                ('triggered_by_id', models.CharField(blank=True, max_length=100, verbose_name='触发对象ID')),
                ('status', models.CharField(choices=[('active', '活跃'), ('acknowledged', '已确认'), ('resolved', '已解决'), ('muted', '已静默')], default='active', max_length=20, verbose_name='状态')),
                ('resolved_at', models.DateTimeField(blank=True, null=True, verbose_name='解决时间')),
                ('resolution_note', models.TextField(blank=True, verbose_name='解决备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='触发时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('rule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='monitoring.alertrule', verbose_name='告警规则')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_alerts', to=settings.AUTH_USER_MODEL, verbose_name='解决人')),
            ],
            options={
                'verbose_name': '告警',
                'verbose_name_plural': '告警',
                'db_table': 'monitoring_alerts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Metric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric_type', models.CharField(choices=[('execution_count', '执行次数'), ('execution_duration', '执行时长'), ('execution_success_rate', '成功率'), ('api_call_count', 'API调用次数'), ('api_call_cost', 'API调用成本'), ('token_usage', 'Token使用量'), ('user_count', '用户数'), ('workflow_count', '工作流数')], max_length=50, verbose_name='指标类型')),
                ('value', models.FloatField(verbose_name='指标值')),
                ('unit', models.CharField(blank=True, max_length=50, verbose_name='单位')),
                ('tags', models.JSONField(default=dict, verbose_name='标签')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='时间戳')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
                ('workflow', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='metrics', to='workflows.workflow', verbose_name='工作流')),
            ],
            options={
                'verbose_name': '指标',
                'verbose_name_plural': '指标',
                'db_table': 'monitoring_metrics',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='NotificationChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='通道名称')),
                ('channel_type', models.CharField(choices=[('email', '邮件'), ('webhook', 'Webhook'), ('slack', 'Slack'), ('discord', 'Discord')], max_length=20, verbose_name='通道类型')),
                ('config', models.JSONField(default=dict, verbose_name='配置')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_channels', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
            ],
            options={
                'verbose_name': '通知通道',
                'verbose_name_plural': '通知通道',
                'db_table': 'monitoring_notification_channels',
                'ordering': ['-created_at'],
            },
        ),

        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
                ('title', models.CharField(max_length=255, verbose_name='标题')),
                ('content', models.TextField(blank=True, verbose_name='内容')),
                ('notification_type', models.CharField(choices=[('info', '信息'), ('success', '成功'), ('warning', '警告'), ('error', '错误'), ('execution', '执行状态'), ('system', '系统通知')], default='info', max_length=20, verbose_name='类型')),
                ('is_read', models.BooleanField(default=False, verbose_name='已读')),
                ('link', models.CharField(blank=True, max_length=500, verbose_name='链接')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='元数据')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '通知',
                'verbose_name_plural': '通知',
                'db_table': 'monitoring_notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['owner', 'is_read', '-created_at'], name='monitoring__owner_i_c095c2_idx'),
        ),

        migrations.AddIndex(
            model_name='executionlog',
            index=models.Index(fields=['workflow_execution', 'timestamp'], name='monitoring__workflow_idx'),
        ),
        migrations.AddIndex(
            model_name='executionlog',
            index=models.Index(fields=['level', 'timestamp'], name='monitoring__level_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['status', 'created_at'], name='monitoring__status_created_idx'),
        ),
        migrations.AddIndex(
            model_name='alert',
            index=models.Index(fields=['severity', 'status'], name='monitoring__severity_status_idx'),
        ),
        migrations.AddIndex(
            model_name='metric',
            index=models.Index(fields=['metric_type', 'timestamp'], name='monitoring__metric_type_idx'),
        ),
        migrations.AddIndex(
            model_name='metric',
            index=models.Index(fields=['user', 'timestamp'], name='monitoring__user_timestamp_idx'),
        ),
    ]
