"""
系统动态功能管理模块
Dynamic Feature Management System
"""

from django.db import models
from django.conf import settings


class FeatureCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="分类名称")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="分类标识")
    description = models.TextField(blank=True, verbose_name="分类描述")
    icon = models.CharField(max_length=50, blank=True, verbose_name="图标")
    sort_order = models.IntegerField(default=0, verbose_name="排序")
    is_expanded = models.BooleanField(default=True, verbose_name="默认展开")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_feature_category"
        verbose_name = "功能分类"
        verbose_name_plural = "功能分类"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class SystemFeature(models.Model):
    VALUE_TYPE_CHOICES = [
        ('boolean', '开关'),
        ('string', '文本'),
        ('integer', '整数'),
        ('float', '小数'),
        ('json', 'JSON对象'),
        ('choice', '选项'),
        ('secret', '密钥'),
    ]

    category = models.ForeignKey(
        FeatureCategory,
        on_delete=models.CASCADE,
        related_name='features',
        verbose_name="分类"
    )
    key = models.CharField(max_length=200, unique=True, verbose_name="标识")
    name = models.CharField(max_length=200, verbose_name="名称")
    description = models.TextField(blank=True, verbose_name="描述")
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default='string', verbose_name="类型")
    value = models.JSONField(default=None, null=True, blank=True, verbose_name="当前值")
    default_value = models.JSONField(default=None, null=True, blank=True, verbose_name="默认值")
    choices = models.JSONField(default=list, blank=True, verbose_name="选项列表")
    min_value = models.FloatField(null=True, blank=True, verbose_name="最小值")
    max_value = models.FloatField(null=True, blank=True, verbose_name="最大值")
    step = models.FloatField(null=True, blank=True, verbose_name="步长")
    placeholder = models.CharField(max_length=500, blank=True, verbose_name="占位符")
    suffix = models.CharField(max_length=50, blank=True, verbose_name="单位")
    group = models.CharField(max_length=100, blank=True, verbose_name="分组")
    order = models.IntegerField(default=0, verbose_name="排序")
    is_enabled = models.BooleanField(default=True, verbose_name="启用")
    is_visible = models.BooleanField(default=True, verbose_name="显示")
    is_readonly = models.BooleanField(default=False, verbose_name="只读")
    source_file = models.CharField(max_length=500, blank=True, verbose_name="来源")
    source_line = models.IntegerField(null=True, blank=True, verbose_name="行号")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_feature"
        verbose_name = "系统功能"
        verbose_name_plural = "系统功能"
        ordering = ["category__sort_order", "order", "key"]
        indexes = [
            models.Index(fields=["key"]),
            models.Index(fields=["category", "is_enabled"]),
        ]

    def __str__(self):
        return f"{self.category.name} / {self.name}"

    def get_value(self):
        if self.value is not None:
            return self.value
        return self.default_value

    def get_display_value(self):
        v = self.get_value()
        if self.value_type == 'boolean':
            return '开启' if v else '关闭'
        if self.value_type == 'secret' and isinstance(v, str) and len(v) > 4:
            return '****' + v[-4:]
        return str(v) if v is not None else ''


class FeatureAuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', '创建'),
        ('update', '修改'),
        ('delete', '删除'),
        ('toggle', '切换'),
        ('reset', '重置'),
    ]

    feature = models.ForeignKey(
        SystemFeature, on_delete=models.CASCADE, related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="操作")
    old_value = models.JSONField(default=None, null=True, blank=True)
    new_value = models.JSONField(default=None, null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='feature_changes'
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reason = models.TextField(blank=True, verbose_name="原因")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "system_feature_audit_log"
        verbose_name = "功能变更日志"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.feature.key} - {self.action}"
