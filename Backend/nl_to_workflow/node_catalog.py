"""
NL 工作流生成可用节点目录
与前端 nodeRegistry 保持语义一致，供 LLM prompt 与校验使用
"""
from typing import Dict

SUPPORTED_NODE_TYPES: Dict[str, str] = {
    # 触发器
    'start': '开始节点（每个工作流仅一个）',
    'end': '结束节点（可多个）',
    'manual': '手动触发（测试执行入口）',
    'schedule': '定时触发（Cron 表达式）',
    'webhook': 'Webhook 触发（接收 HTTP 请求）',
    'form': '表单触发（用户提交表单）',
    # 控制流
    'condition': '条件判断（if/else 分流，需 conditions）',
    'switch': '多分支选择（switch/case）',
    'loop': '循环（for/while/遍历数组）',
    'delay': '延时等待',
    'merge': '合并多路分支数据',
    'split': '批量拆分并行处理',
    'filter': '按条件过滤数据项',
    'subworkflow': '调用子工作流',
    # 数据 I/O
    'input': '输入节点（接收用户/外部数据）',
    'output': '输出节点（返回结果）',
    'variable': '变量读写',
    'set': 'Set 节点（快速设置字段）',
    'code': '代码执行（Python/JS）',
    'transform': '数据映射/过滤/排序',
    'csv_transform': 'CSV 解析与转换',
    'json_transform': 'JSON 解析与构建',
    'datetime': '日期时间格式化与计算',
    'rss_feed': 'RSS/Atom 订阅读取',
    # AI
    'llm': '大语言模型（需 model + prompt）',
    'prompt': '提示词模板',
    'agent': 'AI Agent 自主任务',
    'planner': '任务规划分解',
    'executor': '子任务执行',
    'memory': 'Agent 记忆存储',
    'openai_api': 'OpenAI API 直接调用',
    'huggingface': 'HuggingFace Inference API',
    # HTTP / 工具
    'http': 'HTTP 请求（GET/POST/PUT/DELETE）',
    'tool': '内置工具（搜索/计算器等）',
    'email': 'SMTP 邮件发送',
    'web_scraper': '网页抓取',
    'file_reader': '文件读取',
    'file_writer': '文件写入',
    'document_loader': '文档加载（PDF/Word 等）',
    # RAG
    'embedding': '文本向量化',
    'vector_store': '向量存储',
    'retriever': '向量检索',
    'reranker': '检索结果重排序',
    # 多模态
    'image_generation': 'AI 图像生成',
    'video_generation': 'AI 视频生成',
    'audio_generation': 'AI 音频生成',
    'subtitle_generation': '字幕生成',
    'image_editing': 'AI 图像编辑',
    # MLOps
    'dataset_upload': '数据集上传',
    'data_annotation': '数据标注',
    'data_augmentation': '数据增强',
    'model_training': '模型训练',
    'yolo_training': 'YOLO 目标检测训练',
    'clip_classification': 'CLIP 图像分类/零样本',
    'clip_retrieval': 'CLIP 图文检索索引',
    'project_profiler': '建站前场景与类别分析',
    'project_agent': '项目专属 Agent（改站 + 强制 QA）',
    'model_evaluation': '模型评估',
    'model_deployment': '模型部署',
    'website_generator': 'AI 网站生成脚手架',
    'backend_setup': 'Agent 完善 Flask 后端',
    'frontend_setup': 'Agent 搭建现代化前端',
    'ui_beautify': 'Agent UI 视觉美化',
    'site_code_review': 'Critic 代码复查与修复',
    'environment_provision': 'Desktop 环境与端口预检',
    'site_qa': '生成站 L1–L4 全面 QA',
    'site_preview': '节点内 iframe 本地预览',
    # 通讯协作
    'slack': 'Slack 消息',
    'discord': 'Discord Webhook',
    'telegram': 'Telegram Bot',
    'feishu': '飞书消息',
    'dingtalk': '钉钉机器人',
    'wechat_work': '企业微信机器人',
    'microsoft_teams': 'Microsoft Teams',
    'twilio': 'Twilio 短信/语音',
    'sendgrid': 'SendGrid 邮件',
    'push_notification': '推送通知',
    # 效率工具
    'notion': 'Notion 页面/数据库',
    'google_sheets': 'Google Sheets',
    'google_drive': 'Google Drive',
    'github': 'GitHub Issue/PR',
    'gitlab': 'GitLab',
    'jira': 'Jira Issue',
    'airtable': 'Airtable',
    'trello': 'Trello',
    # 数据库 / 云
    'mysql': 'MySQL 查询',
    'postgres': 'PostgreSQL 查询',
    'mongodb': 'MongoDB',
    'redis': 'Redis 键值',
    'elasticsearch': 'Elasticsearch 搜索',
    'aws_s3': 'AWS S3 对象存储',
    'ftp': 'FTP/SFTP 文件传输',
    'stripe': 'Stripe 支付',
}

# NL 生成时优先推荐的节点（控制 prompt 长度）
NL_PRIMARY_NODE_TYPES = [
    'start', 'end', 'input', 'output', 'llm', 'prompt', 'condition',
    'tool', 'http', 'code', 'email', 'webhook', 'variable', 'transform',
    'delay', 'loop', 'switch', 'feishu', 'dingtalk', 'slack', 'agent',
]
