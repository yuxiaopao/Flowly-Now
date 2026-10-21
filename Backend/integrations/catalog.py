"""Supported connectors. Capabilities here must have an executable service adapter."""

REQUEST_TIMEOUT = 15
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
RESULT_LIMIT = 20
MAX_FIELD_LENGTH = 4096
TEST_MESSAGE = 'Flowly 集成连接测试'
EVENT_LABELS = {
    'execution.started': '工作流开始执行',
    'execution.completed': '工作流执行成功',
    'execution.failed': '工作流执行失败',
}
EXECUTION_EVENTS = {'running': 'execution.started', 'completed': 'execution.completed', 'failed': 'execution.failed', 'timeout': 'execution.failed'}


def field(key, label, *, secret=False, required=True, placeholder='', kind='text'):
    return dict(key=key, label=label, secret=secret, required=required, placeholder=placeholder, kind=kind)


WEBHOOK_FIELD = field('webhook_url', 'Webhook 地址', secret=True, kind='url', placeholder='https://…')
TOKEN_FIELD = field('token', '访问令牌', secret=True)
SIGNING_FIELD = field('secret', '签名密钥', secret=True, required=False, placeholder='已开启签名校验时填写')
BEARER_FIELD = field('token', 'Bearer Token', secret=True, required=False)


def webhook(key, name, category, description, docs, guide, *, fields=None, hosts=(), featured=False):
    return dict(
        id=key, integration_type=key, name=name, category=category, description=description,
        mode='webhook', fields=fields or [WEBHOOK_FIELD], hosts=hosts,
        documentation_url=docs, setup_guide=guide, is_featured=featured,
        capabilities=['发送测试消息', '订阅工作流执行事件'],
        test_notice='测试会向目标发送一条测试消息或触发一次自动化，请使用测试频道或测试流程。',
        scope_note='发送执行状态、工作流名称与执行 ID；不自动传输工作流输入、输出或凭证。目标接收成功不代表后续流程执行完成。',
        sync_label='发送测试消息',
    )


def api(key, name, category, description, docs, guide, *, fields=None, featured=False):
    return dict(
        id=key, integration_type=key, name=name, category=category, description=description,
        mode='api', fields=fields or [TOKEN_FIELD], hosts=(),
        documentation_url=docs, setup_guide=guide, is_featured=featured,
        capabilities=['验证访问权限', description],
        test_notice='测试只读取身份或资源信息，不创建、修改或删除第三方数据。',
        scope_note=f'当前支持：{description}。使用您提供的令牌，不包含 OAuth 授权或自动续期；令牌到期后需更新。每次最多读取 {RESULT_LIMIT} 项。',
        sync_label='读取数据',
    )


CATALOG = [
    webhook('feishu', '飞书', 'communication', '将执行结果发送到飞书群机器人。',
            'https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot',
            '在群设置中添加自定义机器人，复制 Webhook；如启用签名校验，请填写密钥。如启用关键词，请填写测试消息必须包含的关键词。',
            fields=[WEBHOOK_FIELD, SIGNING_FIELD, field('keyword', '安全关键词', required=False)], hosts=('open.feishu.cn',), featured=True),
    webhook('dingtalk', '钉钉', 'communication', '通过自定义机器人发送工作流通知。',
            'https://open.dingtalk.com/document/robots/custom-robot-access',
            '添加自定义机器人并复制完整 Webhook。加签安全设置需填写签名密钥；关键词安全设置需填写相应关键词。',
            fields=[WEBHOOK_FIELD, SIGNING_FIELD, field('keyword', '安全关键词', required=False)], hosts=('oapi.dingtalk.com',), featured=True),
    webhook('wechat_work', '企业微信', 'communication', '向企业微信群机器人发送文本通知。',
            'https://developer.work.weixin.qq.com/document/path/91770',
            '在目标群添加群机器人，复制包含 key 的完整 Webhook 地址。', hosts=('qyapi.weixin.qq.com',), featured=True),
    webhook('slack', 'Slack', 'communication', '通过 Incoming Webhook 发送频道通知。',
            'https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/',
            '在 Slack App 中启用 Incoming Webhooks，授权目标频道后复制 Webhook 地址。', hosts=('hooks.slack.com',)),
    webhook('discord', 'Discord', 'communication', '向 Discord 频道发送 Webhook 消息。',
            'https://docs.discord.com/developers/resources/webhook',
            '在频道设置的集成中创建 Webhook，复制 Webhook URL。', hosts=('discord.com', 'discordapp.com')),
    webhook('microsoft_teams', 'Microsoft Teams', 'communication', '通过 Teams Workflows 接收自适应卡片。',
            'https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook',
            '在 Teams Workflows 创建接收 Webhook 的流程，并配置接收 Adaptive Card。复制 HTTP POST URL；受保护触发器需提供有效的 Bearer Token。',
            fields=[WEBHOOK_FIELD, BEARER_FIELD], hosts=('.logic.azure.com', '.api.powerplatform.com', '.environment.api.powerplatform.com')),
    dict(webhook('telegram', 'Telegram', 'communication', '通过 Telegram Bot 向指定会话发送通知。',
            'https://core.telegram.org/bots/api',
            '通过 BotFather 创建机器人并取得 Token；先在 Telegram 启动机器人，填写目标 Chat ID。测试会调用 sendMessage 验证发送权限。',
            fields=[TOKEN_FIELD, field('chat_id', 'Chat ID', placeholder='例如 -1001234567890')]), mode='telegram'),
    webhook('zapier', 'Zapier', 'automation', '向 Catch Hook 发送事件并触发 Zap。',
            'https://help.zapier.com/hc/en-us/articles/8496288690317-Trigger-Zaps-from-webhooks',
            '创建 Webhooks by Zapier 的 Catch Hook 触发器，复制 URL，发布 Zap 后连接。是否需要付费取决于您的 Zapier 方案。', hosts=('hooks.zapier.com',)),
    webhook('make', 'Make', 'automation', '向 Custom webhook 发送事件并触发场景。',
            'https://help.make.com/webhooks',
            '在 Make 场景添加 Custom webhook，复制 URL 并开启场景。', hosts=('.make.com', '.integromat.com')),
    webhook('n8n', 'n8n', 'automation', '触发 n8n Cloud 或自托管工作流。',
            'https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/',
            '添加 POST Webhook 节点，发布工作流并复制 Production URL。受保护的 Webhook 可使用 Bearer Token；内网地址需由管理员加入服务器允许列表。',
            fields=[WEBHOOK_FIELD, BEARER_FIELD], featured=True),
    webhook('powerautomate', 'Power Automate', 'automation', '向 HTTP 请求触发器发送执行事件。',
            'https://learn.microsoft.com/en-us/power-automate/oauth-authentication',
            '创建 When an HTTP request is received 触发器并保存，复制 HTTP POST URL；受保护触发器需提供有效的 Bearer Token。',
            fields=[WEBHOOK_FIELD, BEARER_FIELD], hosts=('.logic.azure.com', '.api.powerplatform.com', '.environment.api.powerplatform.com')),
    api('github', 'GitHub', 'development', '读取当前账号可访问的仓库列表',
        'https://docs.github.com/en/rest/repos/repos#list-repositories-for-the-authenticated-user',
        '使用 Personal Access Token。私有仓库需授予目标仓库读取权限；测试只验证身份，读取数据时会验证资源权限。', featured=True),
    api('gitlab', 'GitLab', 'development', '读取 GitLab.com 项目列表',
        'https://docs.gitlab.com/api/projects/', '创建具有 read_api 权限的 Personal Access Token。当前接入 GitLab.com。'),
    api('notion', 'Notion', 'productivity', '检索已共享给集成的页面与数据源',
        'https://developers.notion.com/reference/post-search',
        '创建内部集成并复制 Token，在目标页面的 Connections 中授予集成访问权限。未共享的页面不会出现在结果中。', featured=True),
    api('airtable', 'Airtable', 'data', '读取令牌可访问的 Base 列表',
        'https://airtable.com/developers/web/api/list-bases',
        '创建 Personal Access Token，添加 schema.bases:read 权限，并明确授予所需 Base 的访问权限。'),
    api('google_sheets', 'Google Sheets', 'data', '读取指定电子表格的单元格数据',
        'https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/get',
        '启用 Sheets API，提供具有 spreadsheets.readonly 权限的 OAuth Access Token，填写表格 ID 与 A1 范围。Token 不会自动续期。',
        fields=[TOKEN_FIELD, field('spreadsheet_id', '电子表格 ID'), field('range', 'A1 范围', placeholder='Sheet1!A1:Z20')]),
    api('google_drive', 'Google Drive', 'storage', '读取 Google Drive 文件列表',
        'https://developers.google.com/workspace/drive/api/reference/rest/v3/files/list',
        '启用 Drive API，提供具有 drive.metadata.readonly 权限的 OAuth Access Token。Token 不会自动续期。'),
    webhook('custom', '自定义 Webhook', 'data', '通过 HTTP POST 将执行事件交给外部系统。',
            'https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST',
            '填写接收 JSON POST 的 HTTPS 地址。可配置 Bearer Token 和 HMAC-SHA256 签名密钥；签名放在 X-Webhook-Signature 请求头。',
            fields=[WEBHOOK_FIELD, BEARER_FIELD, SIGNING_FIELD]),
]

CONNECTORS = {item['id']: item for item in CATALOG}
INTEGRATION_CHOICES = [(item['id'], item['name']) for item in CATALOG]
API_ENDPOINTS = {
    'github': ('https://api.github.com/user', 'https://api.github.com/user/repos'),
    'gitlab': ('https://gitlab.com/api/v4/user', 'https://gitlab.com/api/v4/projects'),
    'notion': ('https://api.notion.com/v1/users/me', 'https://api.notion.com/v1/search'),
    'airtable': ('https://api.airtable.com/v0/meta/whoami', 'https://api.airtable.com/v0/meta/bases'),
    'google_drive': ('https://www.googleapis.com/drive/v3/about', 'https://www.googleapis.com/drive/v3/files'),
}
SHEETS_ENDPOINT = 'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}'
TELEGRAM_ENDPOINT = 'https://api.telegram.org/bot{token}/sendMessage'
NOTION_VERSION = '2025-09-03'
OFFICIAL_PROXY_HOSTS = tuple({
    'api.github.com', 'gitlab.com', 'api.notion.com', 'api.airtable.com',
    'www.googleapis.com', 'sheets.googleapis.com', 'api.telegram.org',
    *(host for item in CATALOG for host in item.get('hosts', ())),
})


def public_catalog():
    return [{**{key: value for key, value in item.items() if key != 'hosts'},
             'events': list(EVENT_LABELS) if item['mode'] != 'api' else []}
            for item in CATALOG]
