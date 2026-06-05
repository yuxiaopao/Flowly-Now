"""Initial migration for workflows app."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='工作流名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('status', models.CharField(choices=[('draft', '草稿'), ('active', '活跃'), ('paused', '已暂停'), ('archived', '已归档')], default='draft', max_length=20, verbose_name='状态')),
                ('is_published', models.BooleanField(default=False, verbose_name='是否发布')),
                ('is_public', models.BooleanField(default=False, verbose_name='是否公开')),
                ('version', models.IntegerField(default=1, verbose_name='版本号')),
                ('tags', models.JSONField(default=list, verbose_name='标签')),
                ('settings', models.JSONField(default=dict, verbose_name='设置')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflows', to=settings.AUTH_USER_MODEL, verbose_name='所有者')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='versions', to='workflows.workflow', verbose_name='父版本')),
            ],
            options={
                'verbose_name': '工作流',
                'verbose_name_plural': '工作流',
                'db_table': 'workflows',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_type', models.CharField(choices=[('start', '开始'), ('end', '结束'), ('llm', '大语言模型'), ('prompt', '提示词'), ('condition', '条件判断'), ('tool', '工具'), ('input', '输入'), ('output', '输出'), ('code', '代码执行'), ('loop', '循环'), ('variable', '变量'), ('http', 'HTTP请求')], max_length=50, verbose_name='节点类型')),
                ('name', models.CharField(max_length=200, verbose_name='节点名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('position_x', models.IntegerField(default=0, verbose_name='X坐标')),
                ('position_y', models.IntegerField(default=0, verbose_name='Y坐标')),
                ('config', models.JSONField(default=dict, verbose_name='节点配置')),
                ('style', models.JSONField(default=dict, verbose_name='节点样式')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nodes', to='workflows.workflow', verbose_name='所属工作流')),
            ],
            options={
                'verbose_name': '节点',
                'verbose_name_plural': '节点',
                'db_table': 'nodes',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='Edge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(blank=True, max_length=100, verbose_name='标签')),
                ('type', models.CharField(default='default', max_length=50, verbose_name='连线类型')),
                ('animated', models.BooleanField(default=False, verbose_name='是否动画')),
                ('condition', models.JSONField(default=dict, verbose_name='条件')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edges', to='workflows.workflow', verbose_name='所属工作流')),
                ('source_node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_edges', to='workflows.node', verbose_name='源节点')),
                ('target_node', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='incoming_edges', to='workflows.node', verbose_name='目标节点')),
            ],
            options={
                'verbose_name': '连接',
                'verbose_name_plural': '连接',
                'db_table': 'edges',
            },
        ),
        migrations.CreateModel(
            name='WorkflowExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', '等待中'), ('running', '运行中'), ('completed', '已完成'), ('failed', '失败'), ('cancelled', '已取消')], default='pending', max_length=20, verbose_name='状态')),
                ('input_data', models.JSONField(default=dict, verbose_name='输入数据')),
                ('output_data', models.JSONField(default=dict, blank=True, verbose_name='输出数据')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('traceback', models.TextField(blank=True, verbose_name='错误追踪')),
                ('node_status', models.JSONField(default=dict, verbose_name='节点执行状态')),
                ('started_at', models.DateTimeField(auto_now_add=True, verbose_name='开始时间')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('trigger_type', models.CharField(default='manual', max_length=50, verbose_name='触发类型')),
                ('task_id', models.CharField(blank=True, max_length=255, verbose_name='Celery Task ID')),
                ('triggered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='triggered_executions', to=settings.AUTH_USER_MODEL, verbose_name='触发者')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='workflows.workflow', verbose_name='工作流')),
            ],
            options={
                'verbose_name': '执行记录',
                'verbose_name_plural': '执行记录',
                'db_table': 'workflow_executions',
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='WebhookDeliveryLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('webhook_url', models.URLField(max_length=500, verbose_name='Webhook URL')),
                ('request_payload', models.TextField(verbose_name='请求载荷')),
                ('response_status_code', models.IntegerField(blank=True, null=True, verbose_name='响应状态码')),
                ('response_body', models.TextField(blank=True, verbose_name='响应内容')),
                ('status', models.CharField(default='pending', max_length=20, verbose_name='状态')),
                ('success', models.BooleanField(default=False, verbose_name='是否成功')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('retry_count', models.IntegerField(default=0, verbose_name='重试次数')),
                ('duration_ms', models.IntegerField(default=0, verbose_name='耗时(ms)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('execution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhook_logs', to='workflows.workflowexecution', verbose_name='执行记录')),
            ],
            options={
                'verbose_name': 'Webhook投递日志',
                'verbose_name_plural': 'Webhook投递日志',
                'db_table': 'workflow_webhook_delivery_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='workflow',
            index=models.Index(fields=['owner', '-updated_at'], name='workflows_owner_id_fa3a89_idx'),
        ),
        migrations.AddIndex(
            model_name='workflow',
            index=models.Index(fields=['status'], name='workflows_status_8d7a91_idx'),
        ),
        migrations.AddIndex(
            model_name='workflow',
            index=models.Index(fields=['is_published'], name='workflows_is_publ_9e8b02_idx'),
        ),
        migrations.AddIndex(
            model_name='workflowexecution',
            index=models.Index(fields=['workflow', '-started_at'], name='workflow_e_workflo_aa4c72_idx'),
        ),
        migrations.AddIndex(
            model_name='workflowexecution',
            index=models.Index(fields=['status'], name='workflow_e_status_5b5c83_idx'),
        ),
        migrations.AddIndex(
            model_name='workflowexecution',
            index=models.Index(fields=['task_id'], name='workflow_e_task_id_6c6d94_idx'),
        ),
        migrations.AddIndex(
            model_name='webhookdeliverylog',
            index=models.Index(fields=['execution', '-created_at'], name='workflow_w_executi_7d7e85_idx'),
        ),
        migrations.AddIndex(
            model_name='webhookdeliverylog',
            index=models.Index(fields=['status'], name='workflow_w_status_8e8f96_idx'),
        ),
    ]
