"""编辑器实际配置和所有公开数据转换操作的行为契约。"""
import json
import pytest
from workflows.services.langchain_service import LangChainService


def test_xml_fallback_accepts_the_editors_plain_xml_text():
    from workflows.services.data_transform import run_json_transform
    result = run_json_transform(None, {'operation': 'xml_to_json', 'data': '<root><name>中文</name></root>'}, {})
    assert result['success'] is True
    assert result['output']['data'] == {'name': '中文'}


@pytest.mark.parametrize('value', [None, False, 0, [], {}, {'中文': True}, [{'金额': 100}]])
def test_source_reference_preserves_the_upstream_data_type(value):
    from workflows.services.data_transform import run_json_transform
    service = LangChainService()
    result = run_json_transform(service, {'operation': 'json_to_object', 'source': '{{input_data.data}}'}, {'input_data': {'data': value}})
    assert result['success'] is True
    assert result['output']['data'] == value


@pytest.fixture
def service():
    return LangChainService()


@pytest.mark.parametrize('operation,data,schema,expected', [
    ('map', {'id': 7}, {'mappings': [{'from': 'id', 'to': 'userId'}]}, {'userId': 7}),
    ('filter', [{'age': 10}, {'age': 20}], {'condition': 'item.age > 18'}, [{'age': 20}]),
    ('flatten', {'a': {'b': 2}, 'c': [4]}, {'separator': '_'}, {'a_b': 2, 'c_0': 4}),
    ('merge', {'a': 1}, {'other': {'b': 2}}, {'a': 1, 'b': 2}),
    ('json_merge', {'a': {'b': 1}}, {'other': {'a': {'c': 2}}, 'deep': True}, {'a': {'b': 1, 'c': 2}}),
    ('json_path', {'items': [{'v': 1}, {'v': 2}]}, {'path': '$.items[*].v'}, [1, 2]),
    ('json_query', {'items': [{'age': 10}, {'age': 20}]}, {'query': 'items[?age > `18`].age'}, [20]),
    ('json_to_object', '{"名字":"小明"}', {}, {'名字': '小明'}),
    ('xml_to_json', '<root><name>小明</name><age>20</age></root>', {}, {'name': '小明', 'age': '20'}),
    ('parse_array', '结果：[{"x":1}]', {}, [{'x': 1}]),
])
def test_editor_string_configuration(service, operation, data, schema, expected):
    result = service.run_json_transform_node({'operation': operation, 'schema': json.dumps(schema, ensure_ascii=False), 'data': json.dumps(data, ensure_ascii=False)}, {})
    assert result['success'] is True, result
    assert result['output']['data'] == expected


@pytest.mark.parametrize('data', [False, 0, [], {}])
def test_explicit_empty_values_survive(service, data):
    result = service.run_json_transform_node({'operation': 'json_to_object'}, {'data': data, 'other': '无关'})
    assert result['success'] is True
    assert result['output']['data'] == data


def test_json_xml_and_serialization(service):
    output = service.run_json_transform_node({'operation': 'object_to_json'}, {'data': {'名字': '小明'}})
    assert json.loads(output['output']['data']) == {'名字': '小明'}
    output = service.run_json_transform_node({'operation': 'json_to_xml'}, {'data': {'名字': '小明', 'items': [1, 2]}})
    assert output['success'] is True, output
    assert '<名字>小明</名字>' in output['output']['data']


def test_schema_validation_accepts_and_rejects(service):
    config = {'operation': 'json_schema', 'schema': json.dumps({'type': 'object', 'required': ['name'], 'properties': {'name': {'type': 'string'}}})}
    assert service.run_json_transform_node(config, {'data': {'name': '小明'}})['success'] is True
    invalid = service.run_json_transform_node(config, {'data': {'name': 3}})
    assert invalid['success'] is False
    assert invalid['error']


@pytest.mark.parametrize('operation,schema,data', [
    ('map', '{', {}), ('filter', {'condition': '__import__("os")'}, [{}]),
    ('json_path', {'path': 'invalid['}, {}), ('json_query', {'query': '['}, {}),
    ('xml_to_json', {}, '<!DOCTYPE root [<!ENTITY x SYSTEM "file:///etc/passwd">]><root>&x;</root>'),
    ('nonexistent', {}, {}),
])
def test_invalid_json_configs_fail(service, operation, schema, data):
    result = service.run_json_transform_node({'operation': operation, 'schema': schema}, {'data': data})
    assert result['success'] is False, result
    assert result['error']


@pytest.mark.parametrize('operation,params,expected', [
    ('csv_to_json', {}, [{'name': '小明', 'age': 20, 'group': 'a'}, {'name': '小红', 'age': 10, 'group': 'a'}]),
    ('filter', {'column': 'age', 'operator': 'gt', 'value': 18}, [{'name': '小明', 'age': 20, 'group': 'a'}]),
    ('sort', {'column': 'age', 'ascending': True}, [{'name': '小红', 'age': 10, 'group': 'a'}, {'name': '小明', 'age': 20, 'group': 'a'}]),
    ('aggregate', {'groupBy': 'group', 'agg': 'sum', 'target': 'age'}, [{'group': 'a', 'age': 30}]),
    ('join', {'left': 'name', 'right': 'name', 'type': 'inner', 'rightData': [{'name': '小明', 'city': '北京'}]}, [{'name': '小明', 'age': 20, 'group': 'a', 'city': '北京'}]),
    ('pivot', {'index': 'group', 'columns': 'name', 'values': 'age', 'agg': 'sum'}, [{'group': 'a', '小明': 20, '小红': 10}]),
])
def test_csv_editor_configuration(service, operation, params, expected):
    records = [{'name': '小明', 'age': 20, 'group': 'a'}, {'name': '小红', 'age': 10, 'group': 'a'}]
    result = service.run_csv_transform_node({'operation': operation, 'params': json.dumps(params, ensure_ascii=False), 'data': json.dumps(records, ensure_ascii=False)}, {})
    assert result['success'] is True, result
    assert result['output']['data'] == expected


def test_csv_excel_export(service, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    result = service.run_csv_transform_node({'operation': 'csv_to_excel', 'source': '名字,年龄\n小明,20\n'}, {})
    assert result['success'] is True, result
    import pandas as pd
    assert pd.read_excel(result['output']['file_path']).to_dict('records') == [{'名字': '小明', '年龄': 20}]


@pytest.mark.parametrize('operation,params', [('filter', {'column': 'missing'}), ('filter', {'column': 'age', 'operator': 'invalid'}), ('join', {}), ('aggregate', {'column': 'missing'}), ('pivot', {}), ('invalid', {})])
def test_csv_invalid_configuration_fails(service, operation, params):
    result = service.run_csv_transform_node({'operation': operation, 'params': params}, {'data': [{'age': 2}]})
    assert result['success'] is False, result
    assert result['error']
