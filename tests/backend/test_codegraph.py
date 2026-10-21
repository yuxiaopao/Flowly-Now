"""Regression coverage for code graph parsing, caching, APIs, and live refresh."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from rest_framework.test import APIClient

from codegraph import views
from codegraph.routing import websocket_urlpatterns
from codegraph.services.analyzer import GraphAnalyzer
from codegraph.services.cache import GraphCache, ProjectCache, RedisCache
from codegraph.services.parser import CodeParser, CodeStructure, DependencyEdge, FileNode, JavaScriptFuncExtractor


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'pkg').mkdir()
    (tmp_path / 'pkg' / '__init__.py').write_text('', encoding='utf-8')
    (tmp_path / 'pkg' / 'helper.py').write_text('def helper():\n    return 1\n', encoding='utf-8')
    (tmp_path / 'pkg' / 'main.py').write_text(
        'from .helper import helper\nfrom . import helper as helper_module\n'
        'def run():\n    return helper()\n', encoding='utf-8',
    )
    (tmp_path / 'entry.py').write_text('from pkg.main import run\nrun()\n', encoding='utf-8')
    (tmp_path / 'index.js').write_text(
        "import { value } from './lib'\nimport { value as again } from './lib'\n"
        'function start() { return value() }\n', encoding='utf-8',
    )
    (tmp_path / 'lib').mkdir()
    (tmp_path / 'lib' / 'index.ts').write_text('export function value() { return 1 }\n', encoding='utf-8')
    return tmp_path


def test_parser_extracts_functions_real_dependencies_and_root_module(project):
    structure = CodeParser().build_structure(str(project))
    by_path = {node.path.replace('\\', '/'): node for node in structure.nodes}
    assert by_path['entry.py'].module == 'root'
    assert {function.name for function in structure.func_nodes} >= {'helper', 'run', 'start', 'value'}
    pairs = {(edge.source, edge.target) for edge in structure.edges}
    assert (by_path['pkg/main.py'].id, by_path['pkg/helper.py'].id) in pairs
    assert (by_path['entry.py'].id, by_path['pkg/main.py'].id) in pairs
    assert (by_path['index.js'].id, by_path['lib/index.ts'].id) in pairs
    assert len(pairs) == len(structure.edges)
    assert by_path['pkg/helper.py'].imported_by == [by_path['pkg/main.py'].id]


def test_structure_round_trip_and_project_root_isolation(project, tmp_path):
    structure = CodeParser().build_structure(str(project))
    assert CodeStructure.from_dict(json.loads(json.dumps(structure.to_dict()))).to_dict() == structure.to_dict()
    cache = ProjectCache(GraphCache())
    cache.set_structure(1, structure)
    assert isinstance(cache.get_structure(1, str(project)), CodeStructure)
    assert cache.get_structure(1, str(tmp_path / 'other')) is None


def test_shared_parser_does_not_leak_nodes_between_projects(project, tmp_path):
    other = tmp_path / 'other'
    other.mkdir()
    (other / 'index.js').write_text("import './missing'\n", encoding='utf-8')
    parser = CodeParser()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(parser.build_structure, [str(project), str(other)] * 3))
    for result in results[1::2]:
        assert len(result.nodes) == 1
        assert result.edges == []


def test_redis_cache_retains_payload():
    class MemoryRedis:
        def __init__(self):
            self.values = {}

        def setex(self, key, ttl, value):
            self.values[key] = value

        def get(self, key):
            return self.values.get(key)

    cache = RedisCache(MemoryRedis())
    cache.set('graph', {'nodes': [{'id': 'a'}]})
    assert cache.get('graph') == {'nodes': [{'id': 'a'}]}


def test_js_calls_belong_to_their_function_and_line_numbers_are_real():
    source = '\nfunction caller() {\n callee();\n}\nfunction callee() {}\nfunction idle() { return "caller()"; }'
    functions, edges = JavaScriptFuncExtractor().extract(source, 'file')
    assert {(edge.source, edge.target) for edge in edges} == {('file::caller', 'file::callee')}
    caller = next(function for function in functions if function.name == 'caller')
    assert (caller.lineno, caller.end_lineno) == (2, 4)
    vue_functions, _ = JavaScriptFuncExtractor().extract('<template>View</template>\n<script setup>\nfunction run() {}\n</script>', 'view')
    assert vue_functions[0].lineno == 3


def test_directed_bridge_centrality_and_metrics_computed_once(monkeypatch):
    analyzer = GraphAnalyzer()
    structure = CodeStructure(root_path='fixture', nodes=[
        FileNode(id=name, path=name, name=name, extension='.py', size=0, lines=0, module='root')
        for name in ['a', 'b', 'c']
    ], edges=[DependencyEdge(id='ab', source='a', target='b', edge_type='import'),
              DependencyEdge(id='bc', source='b', target='c', edge_type='import')])
    original = analyzer._calculate_all_metrics
    calls = []

    def calculate():
        calls.append(True)
        return original()

    monkeypatch.setattr(analyzer, '_calculate_all_metrics', calculate)
    result = analyzer.analyze(structure, 1, 'Fixture')
    assert len(calls) == 1
    assert result.metrics['b'].centrality == pytest.approx(0.5)
    assert result.metrics['a'].centrality == result.metrics['c'].centrality == 0


@pytest.fixture
def api(project, monkeypatch):
    monkeypatch.setattr(views, 'get_project_config', lambda project_id: {'path': str(project), 'name': 'Fixture'} if project_id == 1 else None)
    monkeypatch.setattr(views, '_project_cache', ProjectCache(GraphCache()))
    client = APIClient()
    client.force_authenticate(user=SimpleNamespace(is_authenticated=True, pk=9127))
    return client


def test_api_repeated_search_and_structure_use_typed_cache(api):
    for _ in range(2):
        response = api.get('/api/v1/codegraph/projects/1/search/', {'q': 'main'})
        assert response.status_code == 200
        assert response.data['results'][0]['name'] == 'main.py'
    response = api.get('/api/v1/codegraph/projects/1/structure/')
    assert response.status_code == 200
    assert response.data['nodes']
    response = api.get('/api/v1/codegraph/projects/1/modules/dependencies/')
    assert response.status_code == 200
    assert response.data['dependencies']


def test_api_analyze_graph_and_error_boundaries(api, monkeypatch):
    response = api.post('/api/v1/codegraph/projects/1/analyze/', {}, format='json')
    assert response.status_code == 200
    analysis = response.data['analysis']
    assert analysis['last_updated']
    assert analysis['stats']['total_functions'] > 0
    assert api.get('/api/v1/codegraph/projects/1/graph/').data == analysis
    assert api.get('/api/v1/codegraph/projects/1/file/', {'path': '../outside.py'}).status_code == 400
    assert api.get('/api/v1/codegraph/projects/1/file/', {'path': 'missing.py'}).status_code == 404
    assert api.get('/api/v1/codegraph/projects/1/search/', {'q': ''}).status_code == 400
    assert api.get('/api/v1/codegraph/projects/99/graph/').status_code == 404
    monkeypatch.setattr(views, 'get_project_config', lambda _: {'path': 'missing-directory', 'name': 'Missing'})
    assert api.post('/api/v1/codegraph/projects/1/analyze/', {}, format='json').status_code == 404
    assert api.get('/api/v1/codegraph/projects/1/search/', {'q': 'main'}).status_code == 404
    assert APIClient().get('/api/v1/codegraph/projects/1/graph/').status_code in (401, 403)


def test_websocket_refresh_keeps_heartbeat_responsive_and_deduplicates(api, project, monkeypatch):
    release = threading.Event()
    started = threading.Event()
    parser = CodeParser()
    calls = []

    def build(path):
        calls.append(path)
        started.set()
        assert release.wait(3)
        return parser.build_structure(path)

    monkeypatch.setattr(views, '_code_parser', SimpleNamespace(build_structure=build))

    async def scenario():
        connection = WebsocketCommunicator(URLRouter(websocket_urlpatterns), '/ws/1/')
        connection.scope['user'] = SimpleNamespace(is_authenticated=True)
        connected, _ = await connection.connect()
        assert connected
        assert (await connection.receive_json_from())['type'] == 'connected'
        try:
            await connection.send_json_to({'type': 'request_refresh'})
            assert await asyncio.to_thread(started.wait, 1)
            await connection.send_json_to({'type': 'request_refresh'})
            await connection.send_json_to({'type': 'ping'})
            assert (await connection.receive_json_from(timeout=1))['type'] == 'pong'
            release.set()
            assert (await connection.receive_json_from(timeout=3))['event'] == 'full_refresh'
            assert len(calls) == 1
            assert views._project_cache.get_analysis(1).stats['total_functions'] > 0
        finally:
            release.set()
            await connection.disconnect()

    asyncio.run(scenario())
