# Generated for website_generator initial schema

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneratedSite',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, verbose_name='网站名称')),
                ('description', models.TextField(blank=True, verbose_name='网站描述')),
                ('model_path', models.CharField(max_length=500, verbose_name='模型路径')),
                ('model_type', models.CharField(default='classification', max_length=50, verbose_name='模型类型')),
                ('labels', models.JSONField(default=list, verbose_name='类别标签')),
                ('framework', models.CharField(default='pytorch', max_length=50, verbose_name='框架')),
                ('training_run_id', models.CharField(blank=True, help_text='关联的 YOLO 训练运行 ID', max_length=100, verbose_name='训练运行ID')),
                ('yolo_version', models.CharField(blank=True, max_length=20, verbose_name='YOLO版本')),
                ('yolo_variant', models.CharField(blank=True, max_length=20, verbose_name='YOLO模型规格')),
                ('best_weight_path', models.CharField(blank=True, max_length=500, verbose_name='最佳权重路径')),
                ('last_weight_path', models.CharField(blank=True, max_length=500, verbose_name='最终权重路径')),
                ('class_names', models.JSONField(default=list, verbose_name='类别名称')),
                ('output_dir', models.CharField(max_length=500, verbose_name='输出目录')),
                ('status', models.CharField(choices=[('generating', '生成中'), ('completed', '已完成'), ('failed', '失败')], default='generating', max_length=20, verbose_name='状态')),
                ('generated_files', models.JSONField(default=list, verbose_name='生成的文件列表')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('progress', models.IntegerField(default=0, verbose_name='进度百分比')),
                ('website_type', models.CharField(choices=[('classification', '图像分类'), ('regression', '回归预测'), ('detection', '目标检测'), ('segmentation', '图像分割'), ('nlp_classification', '文本分类'), ('ner', '命名实体识别')], default='classification', max_length=50, verbose_name='网站类型')),
                ('frontend_framework', models.CharField(choices=[('vue', 'Vue 3'), ('react', 'React'), ('html', '纯HTML/JS')], default='vue', max_length=50, verbose_name='前端框架')),
                ('backend_framework', models.CharField(choices=[('flask', 'Flask'), ('fastapi', 'FastAPI')], default='flask', max_length=50, verbose_name='后端框架')),
                ('inference_endpoint', models.CharField(blank=True, max_length=500, verbose_name='推理端点')),
                ('port', models.IntegerField(default=5000, verbose_name='后端端口')),
                ('codegraph_project_id', models.IntegerField(blank=True, null=True, verbose_name='CodeGraph 项目ID')),
                ('show_in_nav', models.BooleanField(default=True, verbose_name='显示在侧栏导航')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_sites', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='generated_sites', to='tenants.tenant', verbose_name='所属租户')),
            ],
            options={
                'verbose_name': '生成网站',
                'verbose_name_plural': '生成网站',
                'db_table': 'generated_sites',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='generatedsite',
            index=models.Index(fields=['status'], name='generated_s_status_8d0f0d_idx'),
        ),
        migrations.AddIndex(
            model_name='generatedsite',
            index=models.Index(fields=['website_type'], name='generated_s_website_6e8a8a_idx'),
        ),
        migrations.AddIndex(
            model_name='generatedsite',
            index=models.Index(fields=['created_by', '-created_at'], name='generated_s_created_0a8b0a_idx'),
        ),
        migrations.AddIndex(
            model_name='generatedsite',
            index=models.Index(fields=['tenant', '-created_at'], name='generated_s_tenant__1a2b3c_idx'),
        ),
    ]
