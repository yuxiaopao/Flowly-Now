"""
Public auth-page assistant chat (no login required).
"""

import logging
import re

from django.conf import settings
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    from ratelimit.decorators import ratelimit
except ImportError:
    from django_ratelimit.decorators import ratelimit

from gateway.gateway_service import GatewayService

logger = logging.getLogger(__name__)

AUTH_ASSISTANT_SYSTEM_PROMPT = """你是 Flowly 平台的登录页引导助手「小流」，负责友好、简洁地回答访客问题。

Flowly 是可视化 AI 工作流编排平台，支持拖拽编辑、多模型 Agent、RAG、工作流执行与团队协作。

你的职责：
1. 介绍 Flowly 核心能力（工作流、Agent、数据集、训练等）
2. 指导用户在右侧完成登录或注册
3. 回答忘记密码、注册条件等常见问题
4. 语气亲切、专业，每次回复控制在 120 字以内，使用简体中文

限制：
- 不要编造不存在的功能或价格
- 不要要求用户提供密码等敏感信息
- 若问题超出平台范围，礼貌说明并引导联系管理员
"""

MAX_MESSAGE_LEN = 500
MAX_HISTORY_ITEMS = 8


def _normalize_history(history):
    if not isinstance(history, list):
        return []
    cleaned = []
    for item in history[-MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue
        role = item.get('role')
        content = (item.get('content') or '').strip()
        if role not in ('user', 'assistant') or not content:
            continue
        cleaned.append({'role': role, 'content': content[:MAX_MESSAGE_LEN]})
    return cleaned


def get_fallback_reply(message: str) -> str:
    """Rule-based fallback when LLM is unavailable."""
    text = (message or '').strip()
    lower = text.lower()

    if any(k in text for k in ('登录', '登陆', 'sign in', 'log in')) or lower == 'login':
        return (
            '在右侧「登录」标签下输入用户名/邮箱和密码，点击「登录」即可进入平台。'
            '若忘记密码，可点击「忘记密码」通过邮箱重置。'
        )
    if any(k in text for k in ('注册', 'signup', 'sign up', '账号')):
        return (
            '切换到右侧「注册」标签，填写用户名、邮箱和密码并同意服务条款，'
            '即可创建账号。注册成功后请返回登录页登录。'
        )
    if any(k in text for k in ('忘记密码', '重置密码', '找回密码')):
        return '点击登录表单中的「忘记密码」，按提示输入注册邮箱即可收到重置链接。'
    if any(k in text for k in ('工作流', 'workflow', '流程')):
        return (
            'Flowly 支持可视化拖拽搭建 AI 工作流，可串联 LLM、工具、条件分支等节点，'
            '登录后可在「工作流」模块创建与执行。'
        )
    if any(k in text for k in ('agent', '智能体', '机器人')):
        return 'Flowly 支持多 Agent 编排与对话，登录后可在 Agent 模块创建并绑定工具与工作流。'
    if any(k in text for k in ('你好', '您好', 'hello', 'hi', '在吗')):
        return '你好！我是小流，Flowly 的登录页助手。可以问我平台能做什么，或如何登录注册。'
    if any(k in text for k in ('功能', '做什么', '介绍', '是什么')):
        return (
            'Flowly 是 AI 工作流平台：可视化编辑、多模型调用、RAG 知识库、'
            '执行监控与团队协作。登录后即可免费体验核心功能。'
        )
    if re.search(r'价格|收费|费用|多少钱|pricing', lower):
        return '具体计费与套餐以后台配置为准，建议登录后在「设置-账单」查看，或联系站点管理员。'

    return (
        '我是 Flowly 小助手，可以解答登录注册、平台功能等问题。'
        '试试问我：「如何登录？」或「Flowly 能做什么？」'
    )


class PublicAuthAssistantChatView(APIView):
    """POST /api/v1/public/auth-assistant/chat/ — guest chat on login page."""

    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key='ip', rate='30/m', method='POST', block=True))
    def post(self, request):
        message = (request.data.get('message') or '').strip()
        if not message:
            return Response({'error': '请提供消息内容'}, status=status.HTTP_400_BAD_REQUEST)
        if len(message) > MAX_MESSAGE_LEN:
            return Response(
                {'error': f'消息不能超过 {MAX_MESSAGE_LEN} 字'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        history = _normalize_history(request.data.get('history'))
        messages = [{'role': 'system', 'content': AUTH_ASSISTANT_SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({'role': 'user', 'content': message})

        model = getattr(settings, 'AUTH_ASSISTANT_MODEL', None) or getattr(
            settings, 'DEFAULT_LLM_MODEL', 'qwen2.5-coder:7b'
        )

        try:
            gateway = GatewayService(user=None)
            response = gateway.chat(
                messages,
                model=model,
                temperature=0.65,
                max_tokens=320,
                stream=False,
            )
            reply = (response.content or '').strip()
            if not reply:
                reply = get_fallback_reply(message)
            return Response({'reply': reply, 'source': 'llm'})
        except Exception as exc:
            logger.warning('Auth assistant LLM failed, using fallback: %s', exc)
            return Response({
                'reply': get_fallback_reply(message),
                'source': 'fallback',
            })
