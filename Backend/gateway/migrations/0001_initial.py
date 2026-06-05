# Generated migration for gateway app

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
            name='ModelProvider',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='提供商名称')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='标识')),
                ('logo_url', models.URLField(blank=True, verbose_name='Logo URL')),
                ('website', models.URLField(blank=True, verbose_name='官网')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
            ],
            options={
                'verbose_name': '模型提供商',
                'verbose_name_plural': '模型提供商',
                'db_table': 'model_providers',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='AIModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='模型名称')),
                ('model_id', models.CharField(max_length=200, verbose_name='模型ID')),
                ('model_type', models.CharField(choices=[('chat', '对话模型'), ('embedding', '嵌入模型'), ('image', '图像模型'), ('audio', '音频模型')], default='chat', max_length=20, verbose_name='模型类型')),
                ('max_tokens', models.IntegerField(default=4096, verbose_name='最大Token数')),
                ('supports_streaming', models.BooleanField(default=True, verbose_name='支持流式')),
                ('supports_function_calling', models.BooleanField(default=False, verbose_name='支持函数调用')),
                ('supports_vision', models.BooleanField(default=False, verbose_name='支持视觉')),
                ('input_price', models.DecimalField(decimal_places=4, default=0, max_digits=10, verbose_name='输入价格')),
                ('output_price', models.DecimalField(decimal_places=4, default=0, max_digits=10, verbose_name='输出价格')),
                ('default_temperature', models.FloatField(default=0.7, verbose_name='默认温度')),
                ('default_top_p', models.FloatField(default=1.0, verbose_name='默认Top-P')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('is_default', models.BooleanField(default=False, verbose_name='是否为默认')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('context_window', models.IntegerField(default=8192, verbose_name='上下文窗口')),
                ('released_at', models.DateField(blank=True, null=True, verbose_name='发布时间')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='models', to='gateway.modelprovider', verbose_name='提供商')),
            ],
            options={
                'verbose_name': 'AI模型',
                'verbose_name_plural': 'AI模型',
                'db_table': 'ai_models',
                'unique_together': {('provider', 'model_id')},
                'ordering': ['provider', 'name'],
            },
        ),
        migrations.CreateModel(
            name='UserAPIKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('openai', 'OpenAI'), ('anthropic', 'Anthropic'), ('azure', 'Azure OpenAI'), ('google', 'Google AI'), ('custom', '自定义')], max_length=50, verbose_name='服务商')),
                ('name', models.CharField(max_length=100, verbose_name='名称')),
                ('api_key', models.CharField(max_length=500, verbose_name='API Key')),
                ('endpoint', models.URLField(blank=True, verbose_name='API Endpoint')),
                ('api_version', models.CharField(blank=True, max_length=50, verbose_name='API版本')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='最后使用时间')),
                ('total_usage', models.BigIntegerField(default=0, verbose_name='总使用量')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='api_keys', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户API密钥',
                'verbose_name_plural': '用户API密钥',
                'db_table': 'user_api_keys',
                'unique_together': {('user', 'provider', 'name')},
            },
        ),
        migrations.CreateModel(
            name='APICallLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(max_length=50, verbose_name='服务商')),
                ('model', models.CharField(max_length=200, verbose_name='模型')),
                ('endpoint', models.CharField(max_length=500, verbose_name='端点')),
                ('input_tokens', models.IntegerField(default=0, verbose_name='输入Token')),
                ('output_tokens', models.IntegerField(default=0, verbose_name='输出Token')),
                ('total_tokens', models.IntegerField(default=0, verbose_name='总Token')),
                ('latency_ms', models.IntegerField(default=0, verbose_name='延迟(毫秒)')),
                ('status_code', models.IntegerField(default=200, verbose_name='状态码')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('cost', models.DecimalField(decimal_places=6, default=0, max_digits=10, verbose_name='费用')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='时间戳')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='api_logs', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': 'API调用日志',
                'verbose_name_plural': 'API调用日志',
                'db_table': 'api_call_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='apicalllog',
            index=models.Index(fields=['user', 'timestamp'], name='api_call_lo_user_id_d4e9a7_idx'),
        ),
        migrations.AddIndex(
            model_name='apicalllog',
            index=models.Index(fields=['provider', 'timestamp'], name='api_call_lo_provide_5f3b8c_idx'),
        ),
    ]
