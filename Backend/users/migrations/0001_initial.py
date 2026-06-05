"""Initial migration for users app."""

import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('avatar', models.URLField(blank=True, max_length=500, verbose_name='头像')),
                ('role', models.CharField(choices=[('admin', '管理员'), ('developer', '开发者'), ('user', '普通用户')], default='user', max_length=20, verbose_name='角色')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='手机号')),
                ('bio', models.TextField(blank=True, max_length=500, verbose_name='个人简介')),
                ('openai_api_key', models.CharField(blank=True, max_length=500, verbose_name='OpenAI API Key')),
                ('openai_base_url', models.URLField(blank=True, max_length=500, verbose_name='OpenAI Base URL')),
                ('default_model', models.CharField(blank=True, max_length=100, verbose_name='默认模型')),
                ('total_executions', models.IntegerField(default=0, verbose_name='总执行次数')),
                ('monthly_executions', models.IntegerField(default=0, verbose_name='本月执行次数')),
                ('execution_limit', models.IntegerField(default=1000, verbose_name='执行次数限制')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_login_at', models.DateTimeField(blank=True, null=True, verbose_name='最后登录时间')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': '用户',
                'verbose_name_plural': '用户',
                'db_table': 'users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
