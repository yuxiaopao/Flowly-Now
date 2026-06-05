"""
Add new models: NodeExecution, Variable, Tool, APICredential, AuditLog.

Revision ID: 0003_add_new_models
Revises: 0002_add_error_handling
Create Date: 2026-05-09
"""

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0002_add_error_handling'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        # NodeExecution model
        migrations.CreateModel(
            name='NodeExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_version', models.IntegerField(default=1, verbose_name='节点版本')),
                ('status', models.CharField(
                    choices=[
                        ('pending', '等待中'),
                        ('running', '运行中'),
                        ('completed', '已完成'),
                        ('failed', '失败'),
                        ('skipped', '已跳过'),
                    ],
                    default='pending',
                    max_length=20,
                    verbose_name='状态'
                )),
                ('input_data', models.JSONField(blank=True, default=dict, null=True, verbose_name='输入数据')),
                ('output_data', models.JSONField(blank=True, default=dict, null=True, verbose_name='输出数据')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='开始时间')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('duration_ms', models.IntegerField(blank=True, null=True, verbose_name='执行耗时(ms)')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('retry_count', models.IntegerField(default=0, verbose_name='重试次数')),
                ('max_retries_exceeded', models.BooleanField(default=False, verbose_name='超过最大重试')),
                ('model_name', models.CharField(blank=True, max_length=100, verbose_name='模型名称')),
                ('prompt_tokens', models.IntegerField(blank=True, null=True, verbose_name='输入Token')),
                ('completion_tokens', models.IntegerField(blank=True, null=True, verbose_name='输出Token')),
                ('total_tokens', models.IntegerField(blank=True, null=True, verbose_name='总Token')),
                ('model_latency_ms', models.IntegerField(blank=True, null=True, verbose_name='模型延迟(ms)')),
                ('cache_hit', models.BooleanField(default=False, verbose_name='缓存命中')),
                ('cache_key', models.CharField(blank=True, max_length=100, verbose_name='缓存键')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('execution', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='node_executions',
                    to='workflows.workflowexecution',
                    verbose_name='执行记录'
                )),
                ('node', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='executions',
                    to='workflows.node',
                    verbose_name='节点'
                )),
            ],
            options={
                'verbose_name': '节点执行',
                'verbose_name_plural': '节点执行',
                'db_table': 'node_executions',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='nodeexecution',
            index=models.Index(fields=['execution'], name='node_exec_execution_idx'),
        ),
        migrations.AddIndex(
            model_name='nodeexecution',
            index=models.Index(fields=['node'], name='node_exec_node_idx'),
        ),
        migrations.AddIndex(
            model_name='nodeexecution',
            index=models.Index(fields=['status'], name='node_exec_status_idx'),
        ),
        migrations.AddIndex(
            model_name='nodeexecution',
            index=models.Index(fields=['cache_hit'], name='node_exec_cache_idx'),
        ),
        migrations.AddIndex(
            model_name='nodeexecution',
            index=models.Index(fields=['-started_at'], name='node_exec_started_idx'),
        ),

        # Variable model
        migrations.CreateModel(
            name='Variable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='变量名称')),
                ('display_name', models.CharField(blank=True, max_length=200, verbose_name='显示名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('var_type', models.CharField(
                    choices=[
                        ('string', '字符串'),
                        ('number', '数字'),
                        ('boolean', '布尔值'),
                        ('json', 'JSON'),
                        ('array', '数组'),
                        ('secret', '密钥'),
                    ],
                    default='string',
                    max_length=20,
                    verbose_name='变量类型'
                )),
                ('default_value', models.TextField(blank=True, verbose_name='默认值')),
                ('validation_rules', models.JSONField(blank=True, default=dict, verbose_name='验证规则')),
                ('source', models.CharField(
                    choices=[
                        ('user_input', '用户输入'),
                        ('system', '系统'),
                        ('workflow', '工作流'),
                        ('execution', '执行'),
                        ('secret', '密钥库'),
                    ],
                    default='user_input',
                    max_length=20,
                    verbose_name='变量来源'
                )),
                ('secret_path', models.CharField(blank=True, max_length=500, verbose_name='密钥路径')),
                ('is_required', models.BooleanField(default=False, verbose_name='是否必填')),
                ('is_sensitive', models.BooleanField(default=False, verbose_name='是否敏感')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('workflow', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='variables',
                    to='workflows.workflow',
                    verbose_name='所属工作流'
                )),
            ],
            options={
                'verbose_name': '变量',
                'verbose_name_plural': '变量',
                'db_table': 'variables',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='variable',
            index=models.Index(fields=['workflow'], name='var_workflow_idx'),
        ),
        migrations.AddIndex(
            model_name='variable',
            index=models.Index(fields=['var_type'], name='var_type_idx'),
        ),
        migrations.AddIndex(
            model_name='variable',
            index=models.Index(fields=['source'], name='var_source_idx'),
        ),

        # APICredential model
        migrations.CreateModel(
            name='APICredential',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='凭证名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('credential_type', models.CharField(
                    choices=[
                        ('api_key', 'API Key'),
                        ('oauth2', 'OAuth2'),
                        ('basic', 'Basic Auth'),
                        ('bearer', 'Bearer Token'),
                        ('aws', 'AWS'),
                        ('azure', 'Azure'),
                    ],
                    max_length=20,
                    verbose_name='凭证类型'
                )),
                ('credential_data', models.TextField(verbose_name='凭证数据(加密)')),
                ('credential_data_hash', models.CharField(blank=True, max_length=64, verbose_name='凭证数据哈希')),
                ('service_type', models.CharField(
                    blank=True,
                    choices=[
                        ('openai', 'OpenAI'),
                        ('anthropic', 'Anthropic'),
                        ('google', 'Google AI'),
                        ('azure', 'Azure'),
                        ('aws', 'AWS'),
                        ('slack', 'Slack'),
                        ('discord', 'Discord'),
                        ('github', 'GitHub'),
                        ('custom', '自定义'),
                    ],
                    max_length=50,
                    verbose_name='服务类型'
                )),
                ('service_config', models.JSONField(blank=True, default=dict, verbose_name='服务配置')),
                ('scope', models.JSONField(blank=True, default=list, verbose_name='权限范围')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='过期时间')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='最后使用时间')),
                ('usage_count', models.IntegerField(default=0, verbose_name='使用次数')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='api_credentials',
                    to='users.user',
                    verbose_name='所有者'
                )),
            ],
            options={
                'verbose_name': 'API凭证',
                'verbose_name_plural': 'API凭证',
                'db_table': 'api_credentials',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='apicredential',
            index=models.Index(fields=['owner'], name='cred_owner_idx'),
        ),
        migrations.AddIndex(
            model_name='apicredential',
            index=models.Index(fields=['credential_type'], name='cred_type_idx'),
        ),
        migrations.AddIndex(
            model_name='apicredential',
            index=models.Index(fields=['service_type'], name='cred_service_idx'),
        ),
        migrations.AddIndex(
            model_name='apicredential',
            index=models.Index(fields=['is_active'], name='cred_active_idx'),
        ),

        # Tool model
        migrations.CreateModel(
            name='Tool',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='工具名称')),
                ('display_name', models.CharField(blank=True, max_length=200, verbose_name='显示名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('category', models.CharField(blank=True, max_length=100, verbose_name='分类')),
                ('tool_type', models.CharField(
                    choices=[
                        ('builtin', '内置工具'),
                        ('custom', '自定义工具'),
                        ('api', 'API工具'),
                        ('script', '脚本工具'),
                    ],
                    default='custom',
                    max_length=20,
                    verbose_name='工具类型'
                )),
                ('definition', models.JSONField(default=dict, verbose_name='工具定义')),
                ('input_schema', models.JSONField(blank=True, default=dict, verbose_name='输入模式')),
                ('output_schema', models.JSONField(blank=True, default=dict, verbose_name='输出模式')),
                ('auth_type', models.CharField(
                    choices=[
                        ('none', '无'),
                        ('api_key', 'API Key'),
                        ('oauth2', 'OAuth2'),
                        ('basic', 'Basic Auth'),
                        ('bearer', 'Bearer Token'),
                    ],
                    default='none',
                    max_length=20,
                    verbose_name='认证类型'
                )),
                ('timeout_seconds', models.IntegerField(default=30, verbose_name='超时时间(秒)')),
                ('retry_policy', models.JSONField(blank=True, default=dict, verbose_name='重试策略')),
                ('rate_limit', models.JSONField(blank=True, default=dict, verbose_name='速率限制')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='是否启用')),
                ('is_public', models.BooleanField(default=False, verbose_name='是否公开')),
                ('usage_count', models.IntegerField(default=0, verbose_name='使用次数')),
                ('avg_execution_time_ms', models.IntegerField(blank=True, null=True, verbose_name='平均执行时间(ms)')),
                ('success_rate', models.FloatField(default=0, verbose_name='成功率')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('credential', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='tools',
                    to='workflows.apicredential',
                    verbose_name='关联凭证'
                )),
            ],
            options={
                'verbose_name': '工具',
                'verbose_name_plural': '工具',
                'db_table': 'tools',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='tool',
            index=models.Index(fields=['tool_type'], name='tool_type_idx'),
        ),
        migrations.AddIndex(
            model_name='tool',
            index=models.Index(fields=['category'], name='tool_category_idx'),
        ),
        migrations.AddIndex(
            model_name='tool',
            index=models.Index(fields=['is_enabled'], name='tool_enabled_idx'),
        ),

        # AuditLog model
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=100, verbose_name='操作类型')),
                ('resource_type', models.CharField(max_length=50, verbose_name='资源类型')),
                ('resource_id', models.CharField(blank=True, max_length=100, verbose_name='资源ID')),
                ('old_value', models.JSONField(blank=True, null=True, verbose_name='旧值')),
                ('new_value', models.JSONField(blank=True, null=True, verbose_name='新值')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')),
                ('user_agent', models.CharField(blank=True, max_length=500, verbose_name='User Agent')),
                ('request_id', models.CharField(blank=True, max_length=100, verbose_name='请求ID')),
                ('status', models.CharField(
                    choices=[
                        ('success', '成功'),
                        ('failure', '失败'),
                    ],
                    default='success',
                    max_length=20,
                    verbose_name='状态'
                )),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='操作时间')),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audit_logs',
                    to='users.user',
                    verbose_name='操作用户'
                )),
            ],
            options={
                'verbose_name': '审计日志',
                'verbose_name_plural': '审计日志',
                'db_table': 'audit_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', '-timestamp'], name='audit_user_time_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action'], name='audit_action_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['resource_type'], name='audit_res_type_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['resource_id'], name='audit_res_id_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['-timestamp'], name='audit_timestamp_idx'),
        ),
    ]
