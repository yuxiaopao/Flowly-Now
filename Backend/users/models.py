"""
Custom User model for Flowly project.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model with additional fields."""

    ROLE_CHOICES = [
        ('admin', '管理员'),
        ('developer', '开发者'),
        ('user', '普通用户'),
    ]

    # Additional fields
    avatar = models.URLField(max_length=500, blank=True, verbose_name='头像')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name='角色')
    phone = models.CharField(max_length=20, blank=True, verbose_name='手机号')
    bio = models.TextField(max_length=500, blank=True, verbose_name='个人简介')

    # AI related settings
    openai_api_key = models.CharField(max_length=500, blank=True, verbose_name='OpenAI API Key')
    openai_base_url = models.URLField(max_length=500, blank=True, verbose_name='OpenAI Base URL')
    default_model = models.CharField(max_length=100, blank=True, verbose_name='默认模型')

    # Usage tracking
    total_executions = models.IntegerField(default=0, verbose_name='总执行次数')
    monthly_executions = models.IntegerField(default=0, verbose_name='本月执行次数')
    execution_limit = models.IntegerField(default=1000, verbose_name='执行次数限制')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name='最后登录时间')

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
