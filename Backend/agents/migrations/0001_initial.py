"""Initial migration for agents app."""

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
            name='Agent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Agent名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('agent_type', models.CharField(choices=[('conversational', '对话型'), ('task', '任务型'), ('research', '研究型'), ('coding', '编程型')], default='conversational', max_length=50, verbose_name='Agent类型')),
                ('system_prompt', models.TextField(blank=True, verbose_name='系统提示词')),
                ('model', models.CharField(default='gpt-3.5-turbo', max_length=100, verbose_name='使用的模型')),
                ('temperature', models.FloatField(default=0.7, verbose_name='温度参数')),
                ('max_tokens', models.IntegerField(default=2000, verbose_name='最大Token数')),
                ('tools', models.JSONField(default=list, verbose_name='可用工具')),
                ('skills', models.JSONField(default=list, verbose_name='技能')),
                ('memory_enabled', models.BooleanField(default=True, verbose_name='启用记忆')),
                ('context_window', models.IntegerField(default=10, verbose_name='上下文窗口数')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('settings', models.JSONField(default=dict, verbose_name='其他设置')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agents', to=settings.AUTH_USER_MODEL, verbose_name='所有者')),
            ],
            options={
                'verbose_name': 'Agent',
                'verbose_name_plural': 'Agent',
                'db_table': 'agents',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AgentConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('messages', models.JSONField(default=list, verbose_name='消息历史')),
                ('summary', models.TextField(blank=True, verbose_name='对话摘要')),
                ('message_count', models.IntegerField(default=0, verbose_name='消息数')),
                ('token_count', models.IntegerField(default=0, verbose_name='Token数')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='agents.agent', verbose_name='Agent')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agent_conversations', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': 'Agent对话',
                'verbose_name_plural': 'Agent对话',
                'db_table': 'agent_conversations',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='AgentExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', '等待中'), ('running', '运行中'), ('completed', '已完成'), ('failed', '失败')], default='pending', max_length=20)),
                ('input_data', models.JSONField(default=dict, verbose_name='输入数据')),
                ('output_data', models.JSONField(default=dict, blank=True, verbose_name='输出数据')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='agents.agent', verbose_name='Agent')),
                ('conversation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='executions', to='agents.agentconversation', verbose_name='对话')),
            ],
            options={
                'verbose_name': 'Agent执行',
                'verbose_name_plural': 'Agent执行',
                'db_table': 'agent_executions',
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='AgentTool',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='工具名称')),
                ('tool_type', models.CharField(max_length=50, verbose_name='工具类型')),
                ('config', models.JSONField(default=dict, verbose_name='工具配置')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='是否启用')),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agent_tools', to='agents.agent', verbose_name='Agent')),
            ],
            options={
                'verbose_name': 'Agent工具',
                'verbose_name_plural': 'Agent工具',
                'db_table': 'agent_tools',
            },
        ),
    ]
