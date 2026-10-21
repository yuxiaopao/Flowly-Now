"""数据转换节点：统一编辑器字符串配置、类型校验和执行输出。"""
from __future__ import annotations

import ast
import json
import operator
import re
from copy import deepcopy
from io import StringIO
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

JSON_OPERATIONS = frozenset({
    'map', 'filter', 'flatten', 'merge', 'json_merge', 'json_to_object',
    'object_to_json', 'parse_array', 'parse', 'parse_json', 'to_array',
    'extract_array', 'json_to_xml', 'xml_to_json', 'json_schema',
    'json_path', 'json_query',
})
CSV_OPERATIONS = frozenset({'csv_to_json', 'csv_to_excel', 'filter', 'sort', 'aggregate', 'join', 'pivot'})
AGGREGATIONS = frozenset({'sum', 'mean', 'min', 'max', 'count', 'median', 'std', 'var', 'nunique', 'first', 'last'})
COMPARISONS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Gt: operator.gt,
    ast.GtE: operator.ge, ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
}
ARITHMETIC = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod}
CSV_OPERATOR_ALIASES = {'eq': '==', 'ne': '!=', 'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<='}
EXPORT_DIRECTORY = 'exports'
XML_ROOT = 'root'
XML_ITEM = 'item'
DIRECT_PAYLOAD_KEYS = ('data', 'output', 'text', 'content', 'result')
VARIABLE_PAYLOAD_KEYS = ('text', 'content', 'output', 'data', 'result', 'input')


def object_config(value, name):
    if value is None or value == '':
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as exc:
            raise ValueError(f'{name}必须是有效的 JSON 对象：{exc}') from exc
    if not isinstance(value, dict):
        raise ValueError(f'{name}必须是 JSON 对象')
    return value


def extract_payload(context):
    if not isinstance(context, dict):
        return context
    for key in (*DIRECT_PAYLOAD_KEYS, 'input_data'):
        if key in context and context[key] is not None:
            value = context[key]
            if key == 'output' and isinstance(value, dict) and 'data' in value:
                return value['data']
            return value
    variables = context.get('variables')
    if isinstance(variables, dict):
        for key in VARIABLE_PAYLOAD_KEYS:
            if key in variables and variables[key] is not None:
                return variables[key]
    return context


def input_payload(service, config, context):
    if config.get('source'):
        source = str(config['source'])
        reference = re.fullmatch(r'\s*(?:\{\{\s*([\w.]+)\s*\}\}|\{\s*([\w.]+)\s*\})\s*', source)
        if reference:
            path = reference.group(1) or reference.group(2)
            missing = object()
            def lookup(data):
                for key in path.split('.'):
                    if isinstance(data, dict) and key in data:
                        data = data[key]
                    elif isinstance(data, list) and key.isdigit() and int(key) < len(data):
                        data = data[int(key)]
                    else:
                        return missing
                return data
            value = lookup(context)
            if value is missing:
                value = lookup(context.get('variables', {}))
            if value is missing:
                raise ValueError(f'输入变量不存在：{path}')
            return value
        return service._render_template(source, context)
    data = extract_payload(context)
    variables = context.get('variables', {}) if isinstance(context, dict) else {}
    has_payload = not isinstance(context, dict) or (
        any(key in context and context[key] is not None for key in DIRECT_PAYLOAD_KEYS)
        or bool(context.get('input_data'))
        or (isinstance(variables, dict) and any(key in variables and variables[key] is not None for key in VARIABLE_PAYLOAD_KEYS))
    )
    if (data is context or not has_payload) and config.get('data') not in (None, ''):
        raw = config['data']
        if isinstance(raw, str) and (config.get('operation') or config.get('transformType')) == 'xml_to_json' and raw.lstrip().startswith('<'):
            return raw
        return json.loads(raw) if isinstance(raw, str) else raw
    return data


def parse_data(data):
    return json.loads(data) if isinstance(data, str) else data


def field_value(data, path):
    if path.startswith('item.'):
        path = path[len('item.'):]
    current = data
    for key in path.split('.'):
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and key.isdigit():
            current = current[int(key)]
        else:
            return None
    return current


def filter_predicate(expression):
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError('请配置过滤条件，如 item.age > 18')
    tree = ast.parse(expression, mode='eval')
    allowed = (ast.Expression, ast.Constant, ast.Name, ast.Attribute, ast.Subscript,
               ast.List, ast.Tuple, ast.Load, ast.Compare, ast.BoolOp, ast.And,
               ast.Or, ast.UnaryOp, ast.Not, ast.USub, ast.UAdd, ast.BinOp,
               *COMPARISONS, *ARITHMETIC)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError('过滤条件仅支持字段访问、比较、逻辑和基础算术，不能调用函数')

    def evaluate(node, item):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return item if node.id == 'item' else field_value(item, node.id)
        if isinstance(node, ast.Attribute):
            if node.attr.startswith('_'):
                raise ValueError('过滤条件不能访问私有属性')
            value = evaluate(node.value, item)
            return value.get(node.attr) if isinstance(value, dict) else None
        if isinstance(node, ast.Subscript):
            return evaluate(node.value, item)[evaluate(node.slice, item)]
        if isinstance(node, (ast.List, ast.Tuple)):
            return [evaluate(element, item) for element in node.elts]
        if isinstance(node, ast.BoolOp):
            values = (bool(evaluate(value, item)) for value in node.values)
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.UnaryOp):
            value = evaluate(node.operand, item)
            return not value if isinstance(node.op, ast.Not) else -value if isinstance(node.op, ast.USub) else +value
        if isinstance(node, ast.BinOp):
            return ARITHMETIC[type(node.op)](evaluate(node.left, item), evaluate(node.right, item))
        if isinstance(node, ast.Compare):
            left = evaluate(node.left, item)
            for op, right_node in zip(node.ops, node.comparators):
                right = evaluate(right_node, item)
                if not COMPARISONS[type(op)](left, right):
                    return False
                left = right
            return True
        raise ValueError('不支持的过滤表达式')

    return lambda item: bool(evaluate(tree.body, item))


def flatten(data, separator):
    if not isinstance(separator, str) or not separator:
        raise ValueError('展开分隔符不能为空')
    if not isinstance(data, (dict, list)):
        raise ValueError('数据展开需要对象或数组')
    result = {}

    def visit(value, prefix):
        children = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
        if isinstance(value, (dict, list)) and value:
            for key, child in children:
                visit(child, f'{prefix}{separator}{key}' if prefix else str(key))
        elif prefix:
            if prefix in result:
                raise ValueError(f'展开后字段冲突：{prefix}，请更换分隔符')
            result[prefix] = value
    visit(data, '')
    return result


def merge_objects(left, right, deep=False):
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError('JSON 合并需要对象类型')
    result = deepcopy(left)
    for key, value in right.items():
        result[key] = merge_objects(result[key], value, True) if deep and isinstance(result.get(key), dict) and isinstance(value, dict) else deepcopy(value)
    return result


def json_to_xml(data, root_name):
    import re
    def tag(name):
        name = str(name)
        if not re.fullmatch(r'[^\W\d][\w.\-]*', name, re.UNICODE):
            raise ValueError(f'无效的 XML 元素名称：{name}')
        return name
    root = ElementTree.Element(tag(root_name))

    def append(element, value):
        if isinstance(value, dict):
            for key, child in value.items():
                append(ElementTree.SubElement(element, tag(key)), child)
        elif isinstance(value, list):
            for child in value:
                append(ElementTree.SubElement(element, XML_ITEM), child)
        elif value is not None:
            element.text = str(value).lower() if isinstance(value, bool) else str(value)
    append(root, data)
    return ElementTree.tostring(root, encoding='unicode')


def xml_to_json(data):
    from defusedxml.ElementTree import fromstring
    root = fromstring(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    def convert(element):
        children = list(element)
        if not children and not element.attrib:
            return element.text or ''
        result = {f'@{key}': value for key, value in element.attrib.items()}
        for child in children:
            value = convert(child)
            if child.tag in result:
                existing = result[child.tag]
                result[child.tag] = [*existing, value] if isinstance(existing, list) else [existing, value]
            else:
                result[child.tag] = value
        if element.text and element.text.strip():
            result['#text'] = element.text.strip()
        return result
    return convert(root)


def run_json_transform(service, config, context):
    operation = config.get('operation') or config.get('transformType') or 'map'
    try:
        if operation not in JSON_OPERATIONS:
            raise ValueError(f'不支持的 JSON 操作：{operation}')
        schema = object_config(config.get('schema'), '转换模式')
        data = input_payload(service, config, context)
        if operation == 'object_to_json':
            result = json.dumps(data, ensure_ascii=False, indent=2 if config.get('formatting', 'pretty') == 'pretty' else None)
        elif operation == 'xml_to_json':
            result = xml_to_json(data)
        elif operation in ('parse_array', 'parse', 'parse_json', 'to_array', 'extract_array'):
            target = config.get('target_field') or 'items'
            if isinstance(data, str):
                text = data.strip()
                try:
                    data = json.loads(text)
                except ValueError:
                    start, end = text.find('['), text.rfind(']')
                    if start >= 0 and end > start:
                        data = json.loads(text[start:end + 1])
                    else:
                        start, end = text.find('{'), text.rfind('}')
                        data = json.loads(text[start:end + 1]) if start >= 0 and end > start else [text]
            if isinstance(data, dict):
                data = data.get(target, next((data[key] for key in ('chapters', 'items', 'shots', 'scenes', 'data', 'result') if isinstance(data.get(key), list)), [data]))
            result = data if isinstance(data, list) else [data]
            return {'success': True, 'output': {target: result, 'data': result, 'operation': 'parse_array'}}
        else:
            data = parse_data(data)
            if operation == 'json_to_object':
                result = data
            elif operation == 'map':
                mappings = schema.get('mappings')
                if isinstance(mappings, list):
                    if not all(isinstance(item, dict) and item.get('from') and item.get('to') for item in mappings):
                        raise ValueError('字段映射需要完整的 from 和 to')
                    mappings = {item['to']: item['from'] for item in mappings}
                if not isinstance(mappings, dict) or not mappings or not all(isinstance(value, str) for value in mappings.values()):
                    raise ValueError('请配置字段映射 mappings')
                def map_item(item):
                    if not isinstance(item, dict):
                        raise ValueError('字段映射需要对象或对象数组')
                    return {key: field_value(item, value) for key, value in mappings.items()}
                result = [map_item(item) for item in data] if isinstance(data, list) else map_item(data)
            elif operation == 'filter':
                if not isinstance(data, list):
                    raise ValueError('数据过滤需要数组')
                predicate = filter_predicate(schema.get('condition'))
                result = [item for item in data if predicate(item)]
            elif operation == 'flatten':
                result = flatten(data, schema.get('separator', '.'))
            elif operation in ('merge', 'json_merge'):
                result = data
                sources = schema.get('sources')
                if sources is not None:
                    if not isinstance(sources, list) or not sources:
                        raise ValueError('合并 sources 需要非空数组')
                    for source in sources:
                        other = field_value(context, source) if isinstance(source, str) else source
                        result = merge_objects(result, other, schema.get('deep', False))
                else:
                    result = merge_objects(data, schema.get('other', context.get('other_data', {})), schema.get('deep', False))
            elif operation == 'json_to_xml':
                result = json_to_xml(data, schema.get('root', XML_ROOT))
            elif operation == 'json_schema':
                from jsonschema.validators import validator_for
                from referencing import Registry
                validator = validator_for(schema)
                validator.check_schema(schema)
                errors = list(validator(schema, registry=Registry()).iter_errors(data))
                if errors:
                    message = '; '.join(f'{".".join(map(str, error.path)) or "$"}: {error.message}' for error in errors)
                    raise ValueError(f'JSON 模式验证失败：{message}')
                result = data
            elif operation == 'json_path':
                from jsonpath_ng.ext import parse
                path = schema.get('path') or config.get('path')
                if not isinstance(path, str) or not path.strip():
                    raise ValueError('请配置 JSONPath 路径')
                result = [match.value for match in parse(path).find(data)]
            elif operation == 'json_query':
                import jmespath
                query = schema.get('query') or config.get('query')
                if not isinstance(query, str) or not query.strip():
                    raise ValueError('请配置 JMESPath 查询表达式')
                result = jmespath.search(query, data)
        return {'success': True, 'output': {'data': result, 'operation': operation}}
    except Exception as exc:
        return {'success': False, 'error': f'JSON 转换失败：{exc}', 'error_type': 'configuration'}


def run_csv_transform(service, config, context):
    operation = config.get('operation') or config.get('transformType') or 'filter'
    try:
        import pandas as pd
        if operation not in CSV_OPERATIONS:
            raise ValueError(f'不支持的 CSV 操作：{operation}')
        params = object_config(config.get('params'), '操作参数')
        data = input_payload(service, config, context)
        if isinstance(data, str):
            text = data.strip()
            if text.startswith('[') or text.startswith('{'):
                data = json.loads(text)
                frame = pd.DataFrame(data)
            else:
                path = Path(text)
                source = path if '\n' not in text and '\r' not in text and len(text) < 260 and path.is_file() else StringIO(data)
                frame = pd.read_csv(source, sep=config.get('delimiter') or ',')
        else:
            frame = pd.DataFrame(data)

        def require_columns(columns):
            columns = [columns] if isinstance(columns, str) else columns
            if not isinstance(columns, list) or not columns or any(column not in frame.columns for column in columns):
                raise ValueError(f'请配置有效的数据列：{columns}')
            return columns

        if operation == 'filter':
            column = params.get('column')
            require_columns(column)
            op = params.get('operator', '==')
            op = CSV_OPERATOR_ALIASES.get(op, op)
            value = params.get('value', '')
            series = frame[column]
            if op == 'contains':
                mask = series.astype(str).str.contains(str(value), regex=False, na=False)
            elif op in ('==', '!=', '>', '>=', '<', '<='):
                if pd.api.types.is_numeric_dtype(series) and isinstance(value, str):
                    value = float(value)
                functions = {'==': operator.eq, '!=': operator.ne, '>': operator.gt, '>=': operator.ge, '<': operator.lt, '<=': operator.le}
                mask = functions[op](series, value)
            else:
                raise ValueError(f'不支持的过滤运算符：{op}')
            frame = frame[mask]
        elif operation == 'sort':
            columns = require_columns(params.get('column') or params.get('sortField') or config.get('sortField'))
            ascending = params.get('ascending', True)
            if not isinstance(ascending, bool):
                raise ValueError('ascending 必须为布尔值')
            frame = frame.sort_values(columns, ascending=ascending, kind='stable')
        elif operation == 'aggregate':
            column = params.get('column') or params.get('target')
            require_columns(column)
            agg = params.get('aggFunc') or params.get('agg') or 'sum'
            if agg not in AGGREGATIONS:
                raise ValueError(f'不支持的聚合方法：{agg}')
            group = params.get('groupBy')
            if group:
                groups = require_columns(group)
                frame = frame.groupby(groups, dropna=False, as_index=False)[column].agg(agg)
            else:
                value = frame[column].agg(agg)
                value = value.item() if hasattr(value, 'item') else value
                return {'success': True, 'output': {'result': value, 'column': column, 'operation': f'{agg}({column})'}}
        elif operation == 'join':
            left = params.get('left') or params.get('on')
            right = params.get('right') or params.get('on')
            require_columns(left)
            right_frame = pd.DataFrame(parse_data(params.get('rightData', context.get('other_data', []))))
            right_columns = [right] if isinstance(right, str) else right
            if not right_columns or any(column not in right_frame.columns for column in right_columns):
                raise ValueError('请配置右侧连接数据和有效的连接列')
            how = params.get('type') or params.get('how') or 'inner'
            if how not in ('inner', 'left', 'right', 'outer'):
                raise ValueError(f'不支持的连接方式：{how}')
            frame = frame.merge(right_frame, left_on=left, right_on=right, how=how)
        elif operation == 'pivot':
            index, columns, values = (params.get(key) for key in ('index', 'columns', 'values'))
            for column in (index, columns, values):
                require_columns(column)
            agg = params.get('aggFunc') or params.get('agg') or 'mean'
            if agg not in AGGREGATIONS:
                raise ValueError(f'不支持的聚合方法：{agg}')
            frame = frame.pivot_table(index=index, columns=columns, values=values, aggfunc=agg).reset_index()
            frame.columns = [str(column) if not isinstance(column, tuple) else '_'.join(str(part) for part in column if part != '') for column in frame.columns]
        output = {'data': json.loads(frame.to_json(orient='records', force_ascii=False)), 'columns': list(frame.columns), 'rows': len(frame), 'operation': operation}
        if operation == 'csv_to_excel':
            from django.conf import settings
            relative = Path(EXPORT_DIRECTORY) / str(service.user_id or 'anonymous') / f'{uuid4().hex}.xlsx'
            destination = Path(settings.MEDIA_ROOT) / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            # 单元格作为数据保存，避免将用户文本当作 Excel 公式执行。
            with pd.ExcelWriter(destination, engine='openpyxl') as writer:
                frame.to_excel(writer, index=False)
                for row in writer.book.active.iter_rows():
                    for cell in row:
                        if cell.data_type == 'f':
                            cell.data_type = 's'
            output.update(file_path=str(destination), file_url=f'{settings.MEDIA_URL.rstrip("/")}/{relative.as_posix()}', file_name=destination.name)
        return {'success': True, 'output': output}
    except Exception as exc:
        return {'success': False, 'error': f'CSV 转换失败：{exc}', 'error_type': 'configuration'}
