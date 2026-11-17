"""Saved deployment choices remain configurable until real adapters are connected."""
DECLARED_DEPLOYMENT_PLATFORMS = frozenset(('local', 'sagemaker', 'lambdagpu', 'triton'))
DEFAULT_DEPLOYMENT_PLATFORM = 'local'
DEPLOYMENT_NOT_CONFIGURED_MESSAGE = '模型部署服务尚未接入，无法创建或确认真实推理端点。请保留配置并等待部署适配器可用后再执行。'
UNSUPPORTED_PLATFORM_MESSAGE = '不支持此模型部署平台，请选择本地服务、SageMaker、LambdaGPU 或 Triton；这些平台的真实部署适配器当前均未接入。'


def unavailable_deployment(configuration):
    platform = configuration.get('platform', DEFAULT_DEPLOYMENT_PLATFORM)
    known = isinstance(platform, str) and platform in DECLARED_DEPLOYMENT_PLATFORMS
    return {'success': False,
        'error_type': 'deployment_not_configured' if known else 'unsupported_platform',
        'error': DEPLOYMENT_NOT_CONFIGURED_MESSAGE if known else UNSUPPORTED_PLATFORM_MESSAGE}
