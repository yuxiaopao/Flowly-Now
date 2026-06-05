# Generated migration for tenants app

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
            name='Tenant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='租户名称')),
                ('slug', models.SlugField(max_length=100, unique=True, verbose_name='租户标识')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('status', models.CharField(choices=[('active', '活跃'), ('suspended', '暂停'), ('trial', '试用中'), ('cancelled', '已取消')], default='trial', max_length=20, verbose_name='状态')),
                ('plan', models.CharField(choices=[('free', '免费版'), ('starter', '入门版'), ('professional', '专业版'), ('enterprise', '企业版')], default='free', max_length=20, verbose_name='套餐')),
                ('settings', models.JSONField(default=dict, verbose_name='设置')),
                ('custom_domain', models.CharField(blank=True, max_length=255, verbose_name='自定义域名')),
                ('max_users', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='最大用户数')),
                ('max_workflows', models.IntegerField(default=10, validators=[django.core.validators.MinValueValidator(1)], verbose_name='最大工作流数')),
                ('max_executions_per_month', models.IntegerField(default=100, validators=[django.core.validators.MinValueValidator(1)], verbose_name='每月最大执行次数')),
                ('billing_email', models.EmailField(max_length=254, verbose_name='账单邮箱')),
                ('subscription_id', models.CharField(blank=True, max_length=255, verbose_name='订阅ID')),
                ('subscription_end', models.DateTimeField(blank=True, null=True, verbose_name='订阅到期时间')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_tenants', to=settings.AUTH_USER_MODEL, verbose_name='所有者')),
            ],
            options={
                'verbose_name': '租户',
                'verbose_name_plural': '租户',
                'db_table': 'tenants',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TenantUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_month_workflows', models.IntegerField(default=0, verbose_name='本月工作流数')),
                ('current_month_executions', models.IntegerField(default=0, verbose_name='本月执行次数')),
                ('current_month_users', models.IntegerField(default=0, verbose_name='本月用户数')),
                ('total_workflows_created', models.IntegerField(default=0, verbose_name='历史创建工作流数')),
                ('total_executions', models.IntegerField(default=0, verbose_name='历史执行次数')),
                ('total_api_calls', models.IntegerField(default=0, verbose_name='历史API调用数')),
                ('total_tokens_used', models.BigIntegerField(default=0, verbose_name='历史Token使用量')),
                ('last_reset_at', models.DateTimeField(auto_now=True, verbose_name='最后重置时间')),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='usage', to='tenants.tenant', verbose_name='租户')),
            ],
            options={
                'verbose_name': '租户使用量',
                'verbose_name_plural': '租户使用量',
                'db_table': 'tenant_usage',
            },
        ),
        migrations.CreateModel(
            name='TenantMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('owner', '所有者'), ('admin', '管理员'), ('member', '成员'), ('viewer', '查看者')], default='member', max_length=20, verbose_name='角色')),
                ('permissions', models.JSONField(default=list, verbose_name='自定义权限')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否激活')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='tenants.tenant', verbose_name='租户')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tenant_memberships', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
                ('invited_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invitations_sent', to=settings.AUTH_USER_MODEL, verbose_name='邀请人')),
            ],
            options={
                'verbose_name': '租户成员',
                'verbose_name_plural': '租户成员',
                'db_table': 'tenant_memberships',
                'unique_together': {('tenant', 'user')},
                'ordering': ['joined_at'],
            },
        ),
        migrations.CreateModel(
            name='TenantInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, verbose_name='邀请邮箱')),
                ('role', models.CharField(choices=[('owner', '所有者'), ('admin', '管理员'), ('member', '成员'), ('viewer', '查看者')], default='member', max_length=20, verbose_name='邀请角色')),
                ('token', models.CharField(max_length=100, unique=True, verbose_name='邀请令牌')),
                ('status', models.CharField(choices=[('pending', '等待中'), ('accepted', '已接受'), ('expired', '已过期'), ('declined', '已拒绝')], default='pending', max_length=20, verbose_name='状态')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(verbose_name='过期时间')),
                ('accepted_at', models.DateTimeField(blank=True, null=True, verbose_name='接受时间')),
                ('invited_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_invitations', to=settings.AUTH_USER_MODEL, verbose_name='邀请人')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='tenants.tenant', verbose_name='租户')),
            ],
            options={
                'verbose_name': '租户邀请',
                'verbose_name_plural': '租户邀请',
                'db_table': 'tenant_invitations',
                'ordering': ['-created_at'],
            },
        ),
    ]
