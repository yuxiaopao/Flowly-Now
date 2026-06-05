"""Initial migration for prompts app."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workflows', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromptCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='名称')),
                ('slug', models.SlugField(max_length=100, verbose_name='slug')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('icon', models.CharField(default='file-text', max_length=50, verbose_name='图标')),
                ('color', models.CharField(default='#8b5cf6', max_length=20, verbose_name='颜色')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否激活')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='prompts.promptcategory', verbose_name='父分类')),
            ],
            options={
                'verbose_name': '提示词分类',
                'verbose_name_plural': '提示词分类',
                'db_table': 'prompt_categories',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='PromptTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('prompt_type', models.CharField(choices=[('system', '系统提示词'), ('user', '用户提示词'), ('assistant', '助手提示词'), ('task', '任务提示词')], default='task', max_length=20, verbose_name='提示词类型')),
                ('template', models.TextField(verbose_name='提示词模板')),
                ('variables', models.JSONField(default=list, verbose_name='变量定义')),
                ('example_variables', models.JSONField(default=dict, verbose_name='变量示例')),
                ('model_preferences', models.JSONField(default=list, verbose_name='推荐模型')),
                ('temperature', models.FloatField(default=0.7, verbose_name='温度参数')),
                ('max_tokens', models.IntegerField(default=2000, verbose_name='最大Token数')),
                ('tags', models.JSONField(default=list, verbose_name='标签')),
                ('use_count', models.IntegerField(default=0, verbose_name='使用次数')),
                ('success_rate', models.FloatField(default=0, verbose_name='成功率')),
                ('avg_rating', models.FloatField(default=0, verbose_name='平均评分')),
                ('is_public', models.BooleanField(default=False, verbose_name='是否公开')),
                ('share_link', models.CharField(blank=True, max_length=100, verbose_name='分享链接')),
                ('rating_count', models.IntegerField(default=0, verbose_name='评分次数')),
                ('total_rating', models.IntegerField(default=0, verbose_name='总评分')),
                ('version', models.CharField(default='1.0', max_length=20, verbose_name='版本')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否激活')),
                ('is_featured', models.BooleanField(default=False, verbose_name='是否精选')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prompts', to='prompts.promptcategory', verbose_name='分类')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='prompt_templates', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
            ],
            options={
                'verbose_name': '提示词模板',
                'verbose_name_plural': '提示词模板',
                'db_table': 'prompt_templates',
                'ordering': ['-use_count', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PromptUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('node_id', models.CharField(blank=True, max_length=100, verbose_name='节点ID')),
                ('input_variables', models.JSONField(default=dict, verbose_name='输入变量')),
                ('rendered_prompt', models.TextField(blank=True, verbose_name='渲染后的提示词')),
                ('was_successful', models.BooleanField(default=True, verbose_name='是否成功')),
                ('feedback', models.TextField(blank=True, verbose_name='反馈')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('prompt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usages', to='prompts.prompttemplate', verbose_name='提示词')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prompt_usages', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prompt_usages', to='workflows.workflow', verbose_name='工作流')),
            ],
            options={
                'verbose_name': '提示词使用记录',
                'verbose_name_plural': '提示词使用记录',
                'db_table': 'prompt_usages',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PromptVersion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=20, verbose_name='版本号')),
                ('template', models.TextField(verbose_name='提示词模板')),
                ('variables', models.JSONField(default=list, verbose_name='变量定义')),
                ('changelog', models.TextField(blank=True, verbose_name='更新日志')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='prompt_versions', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
                ('prompt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='prompts.prompttemplate', verbose_name='提示词')),
            ],
            options={
                'verbose_name': '提示词版本',
                'verbose_name_plural': '提示词版本',
                'db_table': 'prompt_versions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PromptRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], verbose_name='评分')),
                ('comment', models.TextField(blank=True, verbose_name='评论')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('prompt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='prompts.prompttemplate', verbose_name='提示词')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prompt_ratings', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '提示词评分',
                'verbose_name_plural': '提示词评分',
                'db_table': 'prompt_ratings',
            },
        ),
        migrations.AddField(
            model_name='prompttemplate',
            name='workflows',
            field=models.ManyToManyField(through='prompts.PromptUsage', to='workflows.workflow', verbose_name='使用的工作流'),
        ),
        migrations.AddField(
            model_name='prompttemplate',
            name='tenant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='prompt_templates', to='tenants.tenant', verbose_name='租户'),
        ),
        migrations.AddConstraint(
            model_name='promptversion',
            constraint=models.UniqueConstraint(fields=('prompt', 'version'), name='unique_prompt_version'),
        ),
        migrations.AddConstraint(
            model_name='promptrating',
            constraint=models.UniqueConstraint(fields=('prompt', 'user'), name='unique_prompt_user_rating'),
        ),
    ]
