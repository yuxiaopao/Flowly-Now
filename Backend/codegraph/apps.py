from django.apps import AppConfig


class CodegraphConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'codegraph'
    verbose_name = 'Code Graph Analysis'

    def ready(self):
        # 导入信号处理器
        pass
