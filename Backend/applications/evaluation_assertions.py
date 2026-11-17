"""Deterministic assertions over real request evidence; never eval or model judging."""
import json
import math
import re
from rest_framework.exceptions import ValidationError
from .evaluation_constants import ASSERTION_TYPES, JSON_TYPES, MAX_ASSERTIONS, MAX_ASSERTION_DISPLAY_CHARS, MAX_ASSERTION_VALUE_BYTES

MISSING = object()


def json_pointer(value, pointer):
    if pointer == '':
        return value
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        return MISSING
    current = value
    for token in pointer[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(current, dict):
            current = current.get(token, MISSING)
        elif isinstance(current, list) and re.fullmatch(r'0|[1-9]\d*', token):
            index = int(token)
            current = current[index] if index < len(current) else MISSING
        else:
            return MISSING
    return current


def value_type(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (float, int)):
        return 'number'
    return {dict: 'object', list: 'array', str: 'string'}.get(type(value), 'missing')


def equal_json(left, right):
    if value_type(left) != value_type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(equal_json(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(equal_json(a, b) for a, b in zip(left, right))
    return left == right


def validate_assertions(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ASSERTIONS:
        raise ValidationError(f'每条用例需要 1 至 {MAX_ASSERTIONS} 条断言。')
    result = []
    for row in value:
        if not isinstance(row, dict) or set(row) - {'type', 'path', 'expected'} or row.get('type') not in ASSERTION_TYPES:
            raise ValidationError('断言类型或字段无效。')
        kind = row['type']
        pointer = row.get('path', '')
        if not isinstance(pointer, str) or len(pointer) > 1000 or pointer and (not pointer.startswith('/') or re.search(r'~(?![01])', pointer)):
            raise ValidationError('path 必须是有效 JSON Pointer，例如 /variables/text；根对象使用空字符串。')
        if 'expected' not in row:
            raise ValidationError('断言必须包含 expected。')
        expected = row['expected']
        try:
            encoded = json.dumps(expected, ensure_ascii=False, allow_nan=False)
        except (ValueError, TypeError):
            raise ValidationError('expected 必须是有限 JSON 值。')
        if len(encoded.encode()) > MAX_ASSERTION_VALUE_BYTES:
            raise ValidationError('单条断言的预期值超过服务端大小上限。')
        if kind in ('json_exists', 'grounded') and not isinstance(expected, bool):
            raise ValidationError('存在性和 grounded 的 expected 必须是布尔值。')
        if kind == 'json_type' and expected not in JSON_TYPES:
            raise ValidationError('JSON 类型只能是 object、array、string、number、boolean、null。')
        if kind in ('response_contains', 'error_code') and (not isinstance(expected, str) or not expected or len(expected) > 4000):
            raise ValidationError('文本和错误代码断言需要非空字符串。')
        if kind in ('sources_min', 'latency_max'):
            if isinstance(expected, bool) or not isinstance(expected, (int, float)) or not math.isfinite(expected) or expected < 0:
                raise ValidationError('来源数和最大耗时必须是非负有限数值。')
            if kind == 'sources_min' and (not isinstance(expected, int) or expected > 50):
                raise ValidationError('最少来源数必须是 0 至 50 的整数。')
        if kind != 'json_equals' and kind != 'json_contains' and kind != 'json_exists' and kind != 'json_type' and pointer:
            raise ValidationError('该断言不使用 path。')
        result.append({'type': kind, 'path': pointer, 'expected': expected})
    return result


def display_value(value):
    if value is MISSING:
        return '字段不存在'
    text = json.dumps(value, ensure_ascii=False, allow_nan=False)
    return text[:MAX_ASSERTION_DISPLAY_CHARS] + ('…' if len(text) > MAX_ASSERTION_DISPLAY_CHARS else '')


def check_assertions(record, assertions):
    results = []
    for row in assertions:
        kind, expected = row['type'], row['expected']
        actual = json_pointer(record.output_data, row['path']) if kind.startswith('json_') else MISSING
        passed = False
        if kind == 'json_equals':
            passed = actual is not MISSING and equal_json(actual, expected)
        elif kind == 'json_contains':
            if isinstance(actual, str) and isinstance(expected, str):
                passed = expected in actual
            elif isinstance(actual, list):
                passed = any(equal_json(item, expected) for item in actual)
            elif isinstance(actual, dict) and isinstance(expected, dict):
                passed = all(key in actual and equal_json(actual[key], item) for key, item in expected.items())
        elif kind == 'json_exists':
            passed = (actual is not MISSING) == expected
        elif kind == 'json_type':
            passed = value_type(actual) == expected
        elif kind == 'response_contains':
            actual = (record.output_data or {}).get('response', MISSING) if isinstance(record.output_data, dict) else MISSING
            passed = isinstance(actual, str) and expected in actual
        elif kind == 'grounded':
            actual = (record.output_data or {}).get('grounded', MISSING) if isinstance(record.output_data, dict) else MISSING
            passed = isinstance(actual, bool) and actual == expected
        elif kind == 'sources_min':
            sources = (record.output_data or {}).get('sources') if isinstance(record.output_data, dict) else None
            actual = len(sources) if isinstance(sources, list) else MISSING
            passed = actual is not MISSING and actual >= expected
        elif kind == 'latency_max':
            actual = record.latency_ms
            passed = actual is not None and actual <= expected
        elif kind == 'error_code':
            actual = record.error_code
            passed = record.status in ('failed', 'rejected') and actual == expected
        expected_display = display_value(expected)
        truncated = len(json.dumps(expected, ensure_ascii=False)) > MAX_ASSERTION_DISPLAY_CHARS
        results.append({**row, 'expected': None if truncated else expected, 'expected_display': expected_display,
                        'expected_truncated': truncated, 'passed': bool(passed), 'actual': display_value(actual)})
    return results
