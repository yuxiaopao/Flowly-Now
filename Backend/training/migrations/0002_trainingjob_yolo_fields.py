# Generated manually for YOLO training fields extension
# Reference: training/models.py additions after 0001_initial.py

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('training', '0001_initial'),
    ]

    operations = [
        # Extend TrainingJob status choices (add preparing/pre_validating/validating/packaging/timeout states)
        migrations.AlterField(
            model_name='trainingjob',
            name='status',
            field=models.CharField(
                choices=[
                    ('queued', '排队中'),
                    ('provisioning', '资源分配中'),
                    ('preparing', '准备数据中'),
                    ('running', '训练中'),
                    ('validating', '验证中'),
                    ('packaging', '打包中'),
                    ('completed', '已完成'),
                    ('failed', '失败'),
                    ('cancelled', '已取消'),
                    ('timeout', '超时'),
                ],
                db_index=True,
                default='queued',
                max_length=20,
                verbose_name='状态',
            ),
        ),
        # Add training_kind
        migrations.AddField(
            model_name='trainingjob',
            name='training_kind',
            field=models.CharField(
                choices=[('generic', '通用训练'), ('yolo', 'YOLO训练')],
                db_index=True,
                default='generic',
                max_length=20,
                verbose_name='训练类型',
            ),
        ),
        # Add YOLO-specific fields
        migrations.AddField(
            model_name='trainingjob',
            name='dataset_yaml_path',
            field=models.CharField(blank=True, max_length=500, verbose_name='YOLO数据集配置路径'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='dataset_source_mode',
            field=models.CharField(blank=True, max_length=50, verbose_name='数据集来源模式'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='annotation_project_id',
            field=models.CharField(blank=True, max_length=100, verbose_name='标注项目ID'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='class_names',
            field=models.JSONField(default=list, verbose_name='类别名称'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='best_weight_path',
            field=models.CharField(blank=True, max_length=500, verbose_name='最佳权重路径'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='last_weight_path',
            field=models.CharField(blank=True, max_length=500, verbose_name='最终权重路径'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='exported_artifacts',
            field=models.JSONField(default=dict, verbose_name='导出产物'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='yolo_version',
            field=models.CharField(blank=True, max_length=20, verbose_name='YOLO版本'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='model_variant',
            field=models.CharField(blank=True, max_length=20, verbose_name='YOLO模型规格'),
        ),
        # Add YOLO metrics history fields
        migrations.AddField(
            model_name='trainingjob',
            name='loss_box_history',
            field=models.JSONField(default=list, verbose_name='YOLO Box Loss历史'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='loss_cls_history',
            field=models.JSONField(default=list, verbose_name='YOLO Cls Loss历史'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='loss_dfl_history',
            field=models.JSONField(default=list, verbose_name='YOLO DFL Loss历史'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='precision_history',
            field=models.JSONField(default=list, verbose_name='YOLO Precision历史'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='recall_history',
            field=models.JSONField(default=list, verbose_name='YOLO Recall历史'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='map50_history',
            field=models.JSONField(default=list, verbose_name='YOLO mAP50历史'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='map50_95_history',
            field=models.JSONField(default=list, verbose_name='YOLO mAP50-95历史'),
        ),
        # Add learning_rate, best_epoch, best_fitness, estimated_duration_seconds, eta_seconds, preview_samples
        migrations.AddField(
            model_name='trainingjob',
            name='learning_rate',
            field=models.FloatField(default=0.0, verbose_name='当前学习率'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='best_epoch',
            field=models.IntegerField(default=0, verbose_name='最佳轮次'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='best_fitness',
            field=models.FloatField(default=0.0, verbose_name='最佳适应度'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='estimated_duration_seconds',
            field=models.IntegerField(default=0, verbose_name='预计总时长(秒)'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='eta_seconds',
            field=models.IntegerField(default=0, verbose_name='预计剩余时长(秒)'),
        ),
        migrations.AddField(
            model_name='trainingjob',
            name='preview_samples',
            field=models.JSONField(default=list, verbose_name='验证样例预览'),
        ),
        # Add updated_at
        migrations.AddField(
            model_name='trainingjob',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='更新时间'),
        ),
        # Extend framework choices
        migrations.AlterField(
            model_name='trainingjob',
            name='framework',
            field=models.CharField(
                choices=[
                    ('pytorch', 'PyTorch'),
                    ('transformers', 'Transformers'),
                    ('keras', 'Keras'),
                    ('tensorflow', 'TensorFlow'),
                    ('ultralytics', 'Ultralytics'),
                ],
                max_length=50,
                verbose_name='框架',
            ),
        ),
        # Extend model_type choices
        migrations.AlterField(
            model_name='trainingjob',
            name='model_type',
            field=models.CharField(max_length=50, verbose_name='模型类型'),
        ),
        # Add index on training_kind
        migrations.AddIndex(
            model_name='trainingjob',
            index=models.Index(fields=['training_kind'], name='training_job_training_kind_idx'),
        ),
    ]
