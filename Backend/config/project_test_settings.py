"""全项目测试环境：只使用内存数据库、缓存和消息通道。"""
from .workflow_test_settings import *


class UnmigratedApps(dict):
    def __contains__(self, key):
        return True

    def __getitem__(self, key):
        return None


MIGRATION_MODULES = UnmigratedApps()
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
