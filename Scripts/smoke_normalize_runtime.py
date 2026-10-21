import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from nl_to_workflow.node_config_normalize import _DEFAULT_ENRICH_CODE
from workflows.services.langchain_service import LangChainService

svc = LangChainService.__new__(LangChainService)

parse = svc.run_json_transform_node(
    {'operation': 'parse_array', 'target_field': 'plot_chapters'},
    {'text': 'prefix\n[{"title":"起"},{"title":"承"}]'},
)
print('parse_ok', parse.get('success'), 'count', len(parse.get('output', {}).get('plot_chapters') or []))

code = svc.run_code_node(
    {'code': _DEFAULT_ENRICH_CODE},
    {'input': [{'画面描述': '竹林对决', '情绪': '紧张'}]},
)
print('code_ok', code.get('success'))
print('code_err', (code.get('error') or '')[:2000])
print('code_output', code.get('output'))
