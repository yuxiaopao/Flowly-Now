"""Generate with: python manage.py makemigrations flowly_admin"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('flowly_admin', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LegalDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doc_type', models.CharField(choices=[('terms', '服务条款'), ('privacy', '隐私政策'), ('login', '登录协议')], max_length=20, verbose_name='文档类型')),
                ('version', models.CharField(max_length=32, verbose_name='版本号')),
                ('title', models.CharField(max_length=200, verbose_name='标题')),
                ('content_html', models.TextField(verbose_name='HTML 内容')),
                ('content_markdown', models.TextField(blank=True, verbose_name='Markdown 内容')),
                ('is_active', models.BooleanField(default=False, verbose_name='当前生效')),
                ('require_acceptance', models.BooleanField(default=True, verbose_name='注册需确认')),
                ('effective_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='生效时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_legal_documents', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '法律文档',
                'verbose_name_plural': '法律文档',
                'db_table': 'admin_legal_documents',
                'ordering': ['-effective_at', '-created_at'],
                'unique_together': {('doc_type', 'version')},
            },
        ),
        migrations.CreateModel(
            name='UserTermsAcceptance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_version', models.CharField(max_length=32, verbose_name='确认版本')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP 地址')),
                ('user_agent', models.CharField(blank=True, max_length=500, verbose_name='User Agent')),
                ('accepted_at', models.DateTimeField(auto_now_add=True, verbose_name='确认时间')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='acceptances', to='flowly_admin.legaldocument', verbose_name='文档')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='terms_acceptances', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '条款确认记录',
                'verbose_name_plural': '条款确认记录',
                'db_table': 'admin_user_terms_acceptance',
                'ordering': ['-accepted_at'],
            },
        ),
        migrations.AddIndex(
            model_name='usertermsacceptance',
            index=models.Index(fields=['user', 'document'], name='admin_user__user_id_8a1b2c_idx'),
        ),
        migrations.CreateModel(
            name='FeatureVisibilityRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_key', models.CharField(max_length=200, verbose_name='功能标识')),
                ('scope', models.CharField(choices=[('global', '全局'), ('role', '用户角色'), ('group', '用户组')], default='global', max_length=20, verbose_name='作用范围')),
                ('role', models.CharField(blank=True, max_length=50, verbose_name='角色')),
                ('is_visible', models.BooleanField(default=True, verbose_name='可见')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('group', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='feature_visibility_rules', to='auth.group', verbose_name='用户组')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='feature_visibility_updates', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '功能可见性规则',
                'verbose_name_plural': '功能可见性规则',
                'db_table': 'admin_feature_visibility_rules',
                'ordering': ['feature_key', 'scope'],
            },
        ),
        migrations.CreateModel(
            name='GatewayRouteRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='规则名称')),
                ('path_pattern', models.CharField(max_length=500, verbose_name='路径匹配')),
                ('target_service', models.CharField(max_length=200, verbose_name='目标服务')),
                ('methods', models.JSONField(default=list, verbose_name='HTTP 方法')),
                ('rate_limit_per_minute', models.PositiveIntegerField(default=60, verbose_name='每分钟限流')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='启用')),
                ('priority', models.IntegerField(default=0, verbose_name='优先级')),
                ('config', models.JSONField(blank=True, default=dict, verbose_name='扩展配置')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='gateway_route_updates', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '网关路由规则',
                'verbose_name_plural': '网关路由规则',
                'db_table': 'admin_gateway_route_rules',
                'ordering': ['-priority', 'name'],
            },
        ),
        migrations.CreateModel(
            name='PaymentProviderConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('stripe', 'Stripe'), ('alipay', '支付宝'), ('wechat', '微信支付'), ('paypal', 'PayPal')], max_length=32, verbose_name='支付渠道')),
                ('display_name', models.CharField(max_length=100, verbose_name='显示名称')),
                ('is_enabled', models.BooleanField(default=False, verbose_name='启用')),
                ('config', models.JSONField(blank=True, default=dict, verbose_name='渠道配置')),
                ('fee_rate', models.DecimalField(decimal_places=4, default=0, max_digits=5, verbose_name='费率')),
                ('refund_rules', models.JSONField(blank=True, default=dict, verbose_name='退款规则')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_config_updates', to=settings.AUTH_USER_MODEL, verbose_name='最后修改人')),
            ],
            options={
                'verbose_name': '支付渠道配置',
                'verbose_name_plural': '支付渠道配置',
                'db_table': 'admin_payment_provider_configs',
                'ordering': ['sort_order', 'provider'],
                'unique_together': {('provider',)},
            },
        ),
        migrations.CreateModel(
            name='EmailSendLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('to_email', models.CharField(max_length=254, verbose_name='收件人')),
                ('subject', models.CharField(max_length=500, verbose_name='主题')),
                ('template_key', models.CharField(blank=True, max_length=100, verbose_name='模板标识')),
                ('status', models.CharField(choices=[('queued', '排队中'), ('sent', '已发送'), ('failed', '失败')], default='queued', max_length=20, verbose_name='状态')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('sent_at', models.DateTimeField(blank=True, null=True, verbose_name='发送时间')),
                ('sent_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sent_emails', to=settings.AUTH_USER_MODEL, verbose_name='发送人')),
            ],
            options={
                'verbose_name': '邮件发送记录',
                'verbose_name_plural': '邮件发送记录',
                'db_table': 'admin_email_send_logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BackupRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='文件名')),
                ('file_path', models.CharField(max_length=500, verbose_name='文件路径')),
                ('backup_type', models.CharField(choices=[('full', '完整备份'), ('database', '数据库'), ('files', '文件')], max_length=20, verbose_name='备份类型')),
                ('size', models.BigIntegerField(default=0, verbose_name='大小(字节)')),
                ('status', models.CharField(choices=[('completed', '完成'), ('failed', '失败'), ('in_progress', '进行中')], default='completed', max_length=20, verbose_name='状态')),
                ('include_media', models.BooleanField(default=True, verbose_name='包含媒体文件')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_backups', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
            ],
            options={
                'verbose_name': '备份记录',
                'verbose_name_plural': '备份记录',
                'db_table': 'admin_backup_records',
                'ordering': ['-created_at'],
            },
        ),
    ]
