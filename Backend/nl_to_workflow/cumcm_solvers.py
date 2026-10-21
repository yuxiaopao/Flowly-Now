# -*- coding: utf-8 -*-
"""
CUMCM 专用数值求解器 — 供工作流 Code 节点调用。

支持 solver_type:
  - linear_programming   线性规划 (scipy.optimize.linprog)
  - integer_programming  整数/混合整数规划 (linprog + integrality)
  - regression           回归拟合 (numpy.polyfit)
  - time_series          时间序列预测 (移动平均 + 线性外推)
  - optimization         非线性优化 (scipy.optimize.minimize)
  - monte_carlo          蒙特卡洛模拟 (参数扰动 + 分布统计)
  - generic              通用统计与可行性检查

并提供 build_chart_code() 自动从求解结果生成 matplotlib 图表 (base64 PNG)。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


SOLVER_TYPES: List[str] = [
    'linear_programming',
    'integer_programming',
    'regression',
    'time_series',
    'optimization',
    'monte_carlo',
    'generic',
]


def build_solver_code(index: int) -> str:
    """Return sandbox Python code for sub-problem *index* with auto solver routing."""
    return _SOLVER_CODE_BODY.replace('__IDX__', str(index))


def build_sensitivity_code() -> str:
    """Numeric sensitivity analysis code (numpy perturbation when available)."""
    return _SENSITIVITY_CODE


def build_enhanced_preprocess_code() -> str:
    """Data preprocessing with numpy statistics when available."""
    return _ENHANCED_PREPROCESS_CODE


def build_chart_code(palette: str = 'bw', colors: Optional[List[str]] = None) -> str:
    """Auto-generate matplotlib charts from aggregated sub-problem results.

    Default palette is pure black/white for contest printing (对手产品默认「纯黑白」).
    """
    if colors is None:
        if palette == 'bw':
            colors = ['#000000', '#333333', '#666666', '#999999', '#222222']
        elif palette == 'plain':
            colors = ['#1f2937', '#4b5563', '#6b7280', '#9ca3af', '#374151']
        elif palette == 'modern':
            colors = ['#2563eb', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6']
        else:
            colors = ['#0f172a', '#334155', '#64748b', '#94a3b8', '#cbd5e1']
    while len(colors) < 5:
        colors = list(colors) + ['#000000']
    c0, c1, c2, c3, c4 = colors[0], colors[1], colors[2], colors[3], colors[4]
    code = _CHART_CODE
    # Replace known colorful defaults with palette cycle (order matters: longer first)
    replacements = [
        ('#2563eb', c0),
        ('#ef4444', c1),
        ('#f59e0b', c1),
        ('#10b981', c2),
        ('#8b5cf6', c3),
        ('#6366f1', c4),
    ]
    for old, new in replacements:
        code = code.replace(old, new)
    return code


def build_table_figure_code() -> str:
    """Generate figures/TABLE_*.md summaries (paper-figure skill output)."""
    return _TABLE_FIGURE_CODE


def solver_catalog_for_prompt() -> str:
    """Short catalog text for LLM system prompts."""
    return (
        "solver_type 必须从以下取值：linear_programming | integer_programming | regression | "
        "time_series | optimization | monte_carlo | generic。parameters 须匹配 solver_type：\n"
        "- linear_programming: c, A_ub, b_ub, A_eq(可选), b_eq(可选), bounds\n"
        "- integer_programming: 同 linear_programming，另加 integrality(0连续/1整数/2二进制数组，默认全1)\n"
        "- regression: x(自变量数组), y(因变量数组), degree(默认1)\n"
        "- time_series: series(一维序列), forecast_steps(默认3)\n"
        "- optimization: x0(初值), bounds, objective_type(sum_squares|weighted_sum|rosenbrock), weights(可选)\n"
        "- monte_carlo: baseline(参数字典), coefficients(同名权重), n_simulations(默认1000), "
        "noise_std(默认0.1), seed(可选)\n"
        "- generic: 任意数值 parameters，做描述统计与供需平衡检查"
    )


_EXTRACT_HELPERS = r'''
def _extract_json(text):
    if not isinstance(text, str):
        return None
    s = text.strip().strip('`').replace('```json', '').replace('```', '')
    try:
        if '{' in s:
            return json.loads(s[s.find('{'):s.rfind('}') + 1])
        return json.loads(s)
    except Exception:
        m = re.search(r'\{.*\}', s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _get_upstream_spec(node_outputs, idx):
    spec = {}
    for out in (node_outputs or {}).values():
        if not isinstance(out, dict):
            continue
        t = out.get('text') or ''
        obj = _extract_json(t) if t else None
        if isinstance(obj, dict) and (obj.get('model_name') or obj.get('solver_type') or obj.get('parameters')):
            sp_idx = int(obj.get('subproblem_index') or 0)
            if sp_idx in (0, idx):
                spec = obj
                break
    return spec
'''


_SOLVER_CODE_BODY = (
    '''
import json
import math
import re

# Prefer sandbox-preloaded symbols; catch ALL import failures (OpenBLAS can raise
# MemoryError/OSError, not only ImportError) so parallel solver nodes stay alive.
try:
    np  # noqa: F821 — may already be injected
except NameError:
    np = None
if np is None:
    try:
        import numpy as np
    except Exception:
        np = None

linprog = None
minimize = None
sp_stats = None
try:
    if sp_optimize is not None:  # noqa: F821
        linprog = getattr(sp_optimize, 'linprog', None)
        minimize = getattr(sp_optimize, 'minimize', None)
except Exception:
    pass
try:
    if sp_stats is None and 'sp_stats' in dir():
        pass
except Exception:
    pass
try:
    if linprog is None or minimize is None:
        from scipy.optimize import linprog as _linprog, minimize as _minimize
        linprog = linprog or _linprog
        minimize = minimize or _minimize
except Exception:
    pass
try:
    if sp_stats is None:
        from scipy import stats as sp_stats
except Exception:
    sp_stats = None

idx = __IDX__
raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}

'''
    + _EXTRACT_HELPERS
    + r'''

def _parse_problem_payload(text):
    if not isinstance(text, str) or '{' not in text:
        return None
    return _extract_json(text)


def _get_solver_hint(raw, idx):
    candidates = []
    if isinstance(raw, dict):
        if isinstance(raw.get('solver_hints'), list):
            candidates.append(raw)
        for key in ('input', 'text', 'default_value', 'content', 'user_input', 'prompt'):
            val = raw.get(key)
            if isinstance(val, dict) and isinstance(val.get('solver_hints'), list):
                candidates.append(val)
            elif isinstance(val, str) and 'solver_hints' in val:
                obj = _parse_problem_payload(val)
                if isinstance(obj, dict):
                    candidates.append(obj)
    nos = raw.get('node_outputs') if isinstance(raw, dict) and isinstance(raw.get('node_outputs'), dict) else {}
    for out in nos.values():
        if not isinstance(out, dict):
            continue
        for key in ('text', 'default_value', 'content', 'input', 'user_input', 'prompt'):
            t = out.get(key) or ''
            if not isinstance(t, str) or 'solver_hints' not in t:
                continue
            obj = _parse_problem_payload(t)
            if isinstance(obj, dict):
                candidates.append(obj)
    for payload in candidates:
        for h in payload.get('solver_hints') or []:
            if isinstance(h, dict) and int(h.get('subproblem_index') or 0) == idx:
                return h
    return {}


def _params_usable(solver_type, params):
    if not isinstance(params, dict) or not params:
        return False
    st = (solver_type or '').lower()
    if any(k in st for k in ('linear', 'integer', 'lp', 'mip', '线性', '整数')):
        return isinstance(params.get('c'), list) and len(params.get('c') or []) > 0
    if any(k in st for k in ('regress', '回归')):
        return isinstance(params.get('y'), list) and len(params.get('y') or []) >= 2
    if any(k in st for k in ('monte', '蒙特')):
        return isinstance(params.get('baseline'), dict) and bool(params.get('baseline'))
    if any(k in st for k in ('time', '时序', 'forecast')):
        return isinstance(params.get('series'), list) and len(params.get('series') or []) >= 3
    if any(k in st for k in ('optim', '非线性')):
        return isinstance(params.get('x0'), list) and len(params.get('x0') or []) > 0
    return True


spec = _get_upstream_spec(nos, idx)
hint = _get_solver_hint(raw, idx)
spec_type = (spec.get('solver_type') or spec.get('model_type') or '').lower()
hint_type = (hint.get('solver_type') or '').lower()
# Prefer concrete solver_hints when LLM returns generic/empty or unusable parameters.
if hint_type and (not spec_type or spec_type in ('generic', 'unknown', 'auto') or not _params_usable(spec_type, spec.get('parameters'))):
    spec['solver_type'] = hint.get('solver_type')
if hint.get('parameters') and (
    not isinstance(spec.get('parameters'), dict)
    or not spec.get('parameters')
    or not _params_usable(spec.get('solver_type') or hint_type, spec.get('parameters'))
):
    spec['parameters'] = hint.get('parameters')
elif isinstance(spec.get('parameters'), dict) and isinstance(hint.get('parameters'), dict):
    merged = dict(hint.get('parameters') or {})
    merged.update({k: v for k, v in spec['parameters'].items() if v not in (None, '', [], {})})
    spec['parameters'] = merged

params = spec.get('parameters') if isinstance(spec.get('parameters'), dict) else {}
solver_type = (spec.get('solver_type') or spec.get('model_type') or hint_type or 'generic').lower()

# normalize aliases
if any(k in solver_type for k in ('整数规划', '整数', 'integer', 'mip', '0-1', 'binary')):
    solver_type = 'integer_programming'
elif any(k in solver_type for k in ('线性规划', 'linear', 'lp')) and 'integer' not in solver_type:
    solver_type = 'linear_programming'
elif any(k in solver_type for k in ('回归', 'regress', '拟合')):
    solver_type = 'regression'
elif any(k in solver_type for k in ('时间序列', '时序', 'forecast', 'arima')):
    solver_type = 'time_series'
elif any(k in solver_type for k in ('蒙特卡洛', 'monte', '随机模拟')):
    solver_type = 'monte_carlo'
elif any(k in solver_type for k in ('优化', 'optim', '非线性')):
    solver_type = 'optimization'


def _linprog_solve(p, default_integrality=None):
    if linprog is None:
        return {'status': 'error', 'message': 'scipy.optimize.linprog 不可用'}
    c = p.get('c')
    if c is None:
        return {'status': 'error', 'message': '缺少 parameters.c'}
    A_ub = p.get('A_ub')
    b_ub = p.get('b_ub')
    A_eq = p.get('A_eq')
    b_eq = p.get('b_eq')
    bounds = p.get('bounds')
    integrality = p.get('integrality', default_integrality)
    kwargs = {'method': 'highs'}
    if integrality is not None:
        kwargs['integrality'] = integrality
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, **kwargs)
    return res


def _solve_linear_programming(p):
    res = _linprog_solve(p)
    if isinstance(res, dict):
        return res
    out = {
        'solver': 'linear_programming',
        'success': bool(res.success),
        'x': res.x.tolist() if res.success and res.x is not None else None,
        'objective_value': float(res.fun) if res.success else None,
        'message': str(res.message),
    }
    return out


def _solve_integer_programming(p):
    n = len(p.get('c') or [])
    integrality = p.get('integrality')
    if integrality is None and n:
        integrality = [1] * n
    p2 = dict(p)
    p2['integrality'] = integrality
    res = _linprog_solve(p2, default_integrality=integrality)
    if isinstance(res, dict):
        res['solver'] = 'integer_programming'
        return res
    out = {
        'solver': 'integer_programming',
        'success': bool(res.success),
        'x': res.x.tolist() if res.success and res.x is not None else None,
        'objective_value': float(res.fun) if res.success else None,
        'integrality': integrality,
        'message': str(res.message),
    }
    return out


def _solve_regression(p):
    x = p.get('x')
    y = p.get('y')
    degree = int(p.get('degree') or 1)
    if not isinstance(y, list) or len(y) < 2:
        return {'status': 'error', 'message': '缺少 parameters.y 数组'}
    y_arr = [float(v) for v in y]
    if x is None:
        x_arr = list(range(len(y_arr)))
    elif isinstance(x, list) and x and isinstance(x[0], (list, tuple)):
        x_arr = [float(row[0]) for row in x]
    else:
        x_arr = [float(v) for v in x]
    if np is not None:
        coeffs = np.polyfit(x_arr, y_arr, degree)
        pred = np.polyval(coeffs, x_arr)
        ss_res = float(np.sum((np.array(y_arr) - pred) ** 2))
        ss_tot = float(np.sum((np.array(y_arr) - np.mean(y_arr)) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot else None
        return {
            'solver': 'regression',
            'success': True,
            'x': x_arr,
            'y': y_arr,
            'coefficients': [float(c) for c in coeffs.tolist()],
            'r_squared': round(r2, 6) if r2 is not None else None,
            'fitted': [round(float(v), 6) for v in pred.tolist()],
        }
    # fallback without numpy
    n = len(x_arr)
    sx, sy = sum(x_arr), sum(y_arr)
    sxx = sum(v * v for v in x_arr)
    sxy = sum(x_arr[i] * y_arr[i] for i in range(n))
    denom = n * sxx - sx * sx
    if denom == 0:
        return {'status': 'error', 'message': '自变量无方差，无法回归'}
    a = (n * sxy - sx * sy) / denom
    b = (sy - a * sx) / n
    fitted = [a * v + b for v in x_arr]
    return {
        'solver': 'regression',
        'success': True,
        'x': x_arr,
        'y': y_arr,
        'coefficients': [a, b],
        'note': 'fallback OLS without numpy',
        'fitted': [round(v, 6) for v in fitted],
    }


def _solve_time_series(p):
    series = p.get('series') or p.get('values') or p.get('y')
    steps = int(p.get('forecast_steps') or p.get('horizon') or 3)
    if not isinstance(series, list) or len(series) < 3:
        return {'status': 'error', 'message': '缺少 parameters.series (长度>=3)'}
    vals = [float(v) for v in series]
    window = min(3, len(vals))
    ma = sum(vals[-window:]) / window
    slope = 0.0
    if np is not None and len(vals) >= 2:
        x = np.arange(len(vals), dtype=float)
        slope, intercept = np.polyfit(x, np.array(vals), 1)
        forecast = [float(intercept + slope * (len(vals) + i)) for i in range(steps)]
    else:
        slope = (vals[-1] - vals[0]) / (len(vals) - 1) if len(vals) > 1 else 0.0
        forecast = [vals[-1] + slope * (i + 1) for i in range(steps)]
    return {
        'solver': 'time_series',
        'success': True,
        'series': vals,
        'history_length': len(vals),
        'moving_average_last': round(ma, 6),
        'trend_slope': round(float(slope), 6),
        'forecast': [round(v, 6) for v in forecast],
    }


def _solve_optimization(p):
    if minimize is None or np is None:
        return {'status': 'error', 'message': 'scipy.optimize.minimize / numpy 不可用'}
    x0 = p.get('x0') or p.get('initial')
    if not isinstance(x0, list) or not x0:
        return {'status': 'error', 'message': '缺少 parameters.x0 初值数组'}
    x0_arr = np.array([float(v) for v in x0], dtype=float)
    objective_type = (p.get('objective_type') or 'sum_squares').lower()
    bounds_raw = p.get('bounds')
    bounds = None
    if isinstance(bounds_raw, list):
        bounds = []
        for b in bounds_raw:
            if isinstance(b, (list, tuple)) and len(b) == 2:
                lo = None if b[0] is None else float(b[0])
                hi = None if b[1] is None else float(b[1])
                bounds.append((lo, hi))

    if objective_type == 'weighted_sum':
        weights = p.get('weights') or [1.0] * len(x0_arr)
        w = np.array([float(v) for v in weights], dtype=float)
        def objective(x):
            return float(np.dot(w, x))
    elif objective_type == 'rosenbrock':
        def objective(x):
            return float(np.sum(100.0 * (x[1:] - x[:-1] ** 2) ** 2 + (1 - x[:-1]) ** 2)) if len(x) >= 2 else float(x[0] ** 2)
    else:
        def objective(x):
            return float(np.sum(x ** 2))

    method = p.get('method') or 'Nelder-Mead'
    res = minimize(objective, x0_arr, method=method, bounds=bounds)
    return {
        'solver': 'optimization',
        'success': bool(res.success),
        'x': res.x.tolist() if res.x is not None else None,
        'objective_value': float(res.fun) if res.fun is not None else None,
        'message': str(res.message),
        'objective_type': objective_type,
    }


def _solve_monte_carlo(p):
    if np is None:
        return {'status': 'error', 'message': 'numpy 不可用，无法运行蒙特卡洛模拟'}
    baseline = p.get('baseline') if isinstance(p.get('baseline'), dict) else {}
    if not baseline:
        return {'status': 'error', 'message': '缺少 parameters.baseline 参数字典'}
    coefficients = p.get('coefficients') if isinstance(p.get('coefficients'), dict) else {}
    n_sim = int(p.get('n_simulations') or p.get('n') or 1000)
    n_sim = max(100, min(n_sim, 20000))
    noise_std = float(p.get('noise_std') or 0.1)
    seed = p.get('seed')
    if seed is not None:
        np.random.seed(int(seed))
    objectives = []
    for _ in range(n_sim):
        sample = {}
        for k, v in baseline.items():
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            sample[k] = fv * (1.0 + np.random.normal(0.0, noise_std))
        obj = 0.0
        for k, val in sample.items():
            weight = float(coefficients.get(k, 1.0))
            obj += weight * val
        objectives.append(obj)
    arr = np.array(objectives, dtype=float)
    percentiles = [5, 25, 50, 75, 95]
    pct = {str(q): float(np.percentile(arr, q)) for q in percentiles}
    return {
        'solver': 'monte_carlo',
        'success': True,
        'n_simulations': n_sim,
        'noise_std': noise_std,
        'mean': float(np.mean(arr)),
        'std': float(np.std(arr)),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'percentiles': pct,
        'objective_value': float(np.mean(arr)),
        'histogram': {
            'counts': np.histogram(arr, bins=20)[0].tolist(),
            'bin_edges': np.histogram(arr, bins=20)[1].tolist(),
        },
    }


def _solve_generic(p):
    nums = [v for v in p.values() if isinstance(v, (int, float))]
    out = {}
    if nums:
        out['param_count'] = len(nums)
        out['param_sum'] = round(sum(nums), 6)
        out['param_mean'] = round(sum(nums) / len(nums), 6)
        out['param_min'] = min(nums)
        out['param_max'] = max(nums)
    demand = p.get('demand') or p.get('demands')
    supply = p.get('supply') or p.get('supply_capacity')
    if isinstance(demand, list) and isinstance(supply, list):
        td = sum(float(x) for x in demand)
        ts = sum(float(x) for x in supply)
        out['total_demand'] = round(td, 6)
        out['total_supply'] = round(ts, 6)
        out['supply_demand_gap'] = round(ts - td, 6)
        out['feasible'] = ts >= td
    return {'solver': 'generic', 'success': bool(out), 'computed': out}


_dispatch = {
    'linear_programming': _solve_linear_programming,
    'integer_programming': _solve_integer_programming,
    'regression': _solve_regression,
    'time_series': _solve_time_series,
    'optimization': _solve_optimization,
    'monte_carlo': _solve_monte_carlo,
    'generic': _solve_generic,
}

computed = _dispatch.get(solver_type, _solve_generic)(params)
results = {
    'subproblem_index': idx,
    'model_name': spec.get('model_name') or f'子问题{idx}模型',
    'solver_type': solver_type,
    'computed': computed,
    'status': 'ok' if computed.get('success') or computed.get('computed') else 'needs_manual_review',
}

def _sanitize(obj):
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if np is not None:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.generic):
            return obj.item()
    return obj

results = _sanitize(results)
results['text'] = json.dumps(results, ensure_ascii=False, default=str)
output = results
'''
)


_ENHANCED_PREPROCESS_CODE = r'''
import json
import math
import re

try:
    import numpy as np
except ImportError:
    np = None

raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and (
    'node_outputs' in raw['input'] or 'variables' in raw['input'] or 'text' in raw['input']
):
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}


def _extract_json(text):
    if not isinstance(text, str):
        return None
    s = text.strip().strip('`').replace('```json', '').replace('```', '')
    try:
        if '{' in s:
            return json.loads(s[s.find('{'):s.rfind('}') + 1])
        return json.loads(s)
    except Exception:
        m = re.search(r'\{.*\}', s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None

problem_payload = None
# Prefer parsed JSON from the current input payload (string or dict).
for key in ('input', 'text', 'default_value', 'content', 'user_input', 'prompt'):
    val = raw.get(key) if isinstance(raw, dict) else None
    if isinstance(val, dict) and ('problem_text' in val or 'data' in val or 'solver_hints' in val):
        problem_payload = val
        break
    if isinstance(val, str) and ('problem_text' in val or 'solver_hints' in val or '"data"' in val):
        problem_payload = _extract_json(val)
        if problem_payload:
            break

if problem_payload is None:
    for out in nos.values():
        if not isinstance(out, dict):
            continue
        for key in ('text', 'default_value', 'content', 'input', 'user_input', 'prompt'):
            t = out.get(key) or ''
            if isinstance(t, str) and ('problem_text' in t or 'solver_hints' in t or '"data"' in t):
                problem_payload = _extract_json(t)
                if problem_payload:
                    break
            dv = out.get(key)
            if isinstance(dv, dict) and ('problem_text' in dv or 'data' in dv):
                problem_payload = dv
                break
        if problem_payload:
            break

stats = {'numeric_fields': [], 'matrix_fields': [], 'counts': {}, 'warnings': []}
data = (problem_payload or {}).get('data') or {}

for key, val in data.items():
    if isinstance(val, list) and val and all(isinstance(x, (int, float)) for x in val):
        if np is not None:
            arr = np.array([float(x) for x in val], dtype=float)
            stats['numeric_fields'].append({
                'field': key,
                'count': int(arr.size),
                'min': float(np.min(arr)),
                'max': float(np.max(arr)),
                'mean': float(np.round(np.mean(arr), 6)),
                'std': float(np.round(np.std(arr), 6)),
                'sum': float(np.round(np.sum(arr), 6)),
                'median': float(np.round(np.median(arr), 6)),
            })
        else:
            n = len(val)
            mean = sum(val) / n
            var = sum((x - mean) ** 2 for x in val) / n
            stats['numeric_fields'].append({
                'field': key,
                'count': n,
                'min': min(val),
                'max': max(val),
                'mean': round(mean, 6),
                'std': round(math.sqrt(var), 6),
                'sum': round(sum(val), 6),
            })
    elif isinstance(val, list) and val and isinstance(val[0], list):
        stats['matrix_fields'].append({'field': key, 'shape': [len(val), len(val[0]) if val[0] else 0]})
    elif isinstance(val, list):
        stats['counts'][key] = len(val)

if not stats['numeric_fields'] and not stats['matrix_fields']:
    stats['warnings'].append('未发现可直接统计的数值数组，后续建模需依赖 LLM 推断或补充数据')

output = {
    'problem_payload': problem_payload,
    'descriptive_stats': stats,
    'numpy_available': np is not None,
    'text': json.dumps({'descriptive_stats': stats, 'data_keys': list(data.keys())}, ensure_ascii=False),
}
'''


_SENSITIVITY_CODE = r'''
import json
import re

try:
    import numpy as np
except ImportError:
    np = None

raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}

results = []
for out in nos.values():
    if not isinstance(out, dict):
        continue
    t = out.get('text') or ''
    if not isinstance(t, str) or 'subproblem_index' not in t:
        continue
    try:
        obj = json.loads(t[t.find('{'):t.rfind('}') + 1] if '{' in t else t)
    except Exception:
        continue
    if not isinstance(obj, dict):
        continue
    comp = obj.get('computed') if isinstance(obj.get('computed'), dict) else obj
    if not isinstance(comp, dict):
        continue
    base_obj = comp.get('objective_value')
    if base_obj is None and isinstance(comp.get('computed'), dict):
        base_obj = comp['computed'].get('param_mean')
    if base_obj is None:
        continue
    try:
        base = float(base_obj)
    except (TypeError, ValueError):
        continue
    perturbations = []
    for delta in (-0.2, -0.1, 0.1, 0.2):
        perturbed = base * (1 + delta)
        perturbations.append({
            'delta_pct': int(delta * 100),
            'baseline': round(base, 6),
            'perturbed_value': round(perturbed, 6),
            'relative_change': round(delta, 4),
        })
    results.append({
        'subproblem_index': obj.get('subproblem_index'),
        'metric': 'objective_value' if comp.get('objective_value') is not None else 'proxy',
        'baseline': round(base, 6),
        'perturbations': perturbations,
    })

output = {
    'sensitivity_numeric': results,
    'count': len(results),
    'numpy_available': np is not None,
    'text': json.dumps({'sensitivity_numeric': results}, ensure_ascii=False),
}
'''


_CHART_CODE = r'''
import json
import re
import base64
import io

# Use sandbox-preloaded plt/np (re-importing matplotlib triggers blocked os module)
np = globals().get('np') or globals().get('numpy')
plt = globals().get('plt')

raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}


def _parse_obj(text):
    if not isinstance(text, str) or '{' not in text:
        return None
    s = text.strip().strip('`').replace('```json', '').replace('```', '')
    try:
        return json.loads(s[s.find('{'):s.rfind('}') + 1])
    except Exception:
        m = re.search(r'\{.*\}', s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('ascii')


def _simple_svg_bar(labels, values, title):
    w, h = 480, 320
    pad = 40
    max_v = max(values) if values else 1
    max_v = max_v if max_v else 1
    bar_w = max(20, (w - 2 * pad) // max(len(labels), 1) - 8)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">',
        f'<rect width="100%" height="100%" fill="#fafafa"/>',
        f'<text x="{w//2}" y="24" text-anchor="middle" font-size="14">{title}</text>',
    ]
    for i, (lab, val) in enumerate(zip(labels, values)):
        bh = int((h - 2 * pad) * float(val) / max_v)
        x = pad + i * (bar_w + 8)
        y = h - pad - bh
        parts.append(f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bh}" fill="#2563eb"/>')
        parts.append(f'<text x="{x + bar_w//2}" y="{h - pad + 16}" text-anchor="middle" font-size="11">{lab}</text>')
    parts.append('</svg>')
    svg = ''.join(parts)
    return base64.b64encode(svg.encode('utf-8')).decode('ascii')


sub_results = []
for out in nos.values():
    if not isinstance(out, dict):
        continue
    obj = _parse_obj(out.get('text') or '')
    if isinstance(obj, dict) and obj.get('subproblem_index') is not None:
        sub_results.append(obj)
    elif isinstance(obj, dict) and isinstance(obj.get('subproblem_results'), list):
        sub_results.extend(obj['subproblem_results'])

charts = []
markdown_embeds = []
fig_no = 0

for item in sub_results:
    idx = item.get('subproblem_index')
    comp = item.get('computed') if isinstance(item.get('computed'), dict) else {}
    solver = comp.get('solver') or item.get('solver_type') or 'generic'
    title_prefix = f'问{idx} ' if idx else ''
    chart_title = ''
    b64 = None
    chart_type = solver

    try:
        if solver in ('regression',) and comp.get('fitted'):
            y_vals = comp.get('y')
            fitted = comp['fitted']
            x_raw = comp.get('x') or list(range(len(fitted)))
            chart_title = f'{title_prefix}回归拟合图'[:15]
            if plt is not None:
                fig, ax = plt.subplots(figsize=(6, 4))
                if y_vals:
                    ax.scatter(x_raw, y_vals, label='观测值', color='#2563eb')
                ax.plot(x_raw, fitted, label='拟合曲线', color='#ef4444')
                ax.set_title(chart_title)
                ax.set_xlabel('自变量')
                ax.set_ylabel('因变量')
                ax.legend()
                ax.grid(True, alpha=0.3)
                b64 = _fig_to_base64(fig)
                plt.close(fig)
            else:
                b64 = _simple_svg_bar([str(x) for x in x_raw[:6]], [float(v) for v in fitted[:6]], chart_title)
                chart_type = 'svg_bar'
        elif solver in ('time_series',):
            series = comp.get('series') or comp.get('history')
            forecast = comp.get('forecast')
            if isinstance(forecast, list) and isinstance(series, list):
                hist = [float(v) for v in series]
                fc = [float(v) for v in forecast]
                chart_title = f'{title_prefix}时序预测'[:15]
                if plt is not None:
                    xs = list(range(len(hist)))
                    xf = list(range(len(hist), len(hist) + len(fc)))
                    fig, ax = plt.subplots(figsize=(6, 4))
                    ax.plot(xs, hist, 'o-', label='历史序列', color='#2563eb')
                    ax.plot(xf, fc, 's--', label='预测值', color='#f59e0b')
                    ax.set_title(chart_title)
                    ax.set_xlabel('时间步')
                    ax.set_ylabel('序列值')
                    ax.legend()
                    ax.grid(True, alpha=0.3)
                    b64 = _fig_to_base64(fig)
                    plt.close(fig)
                else:
                    labels = [str(i) for i in range(len(hist) + len(fc))]
                    b64 = _simple_svg_bar(labels[:8], (hist + fc)[:8], chart_title)
                    chart_type = 'svg_bar'
        elif solver in ('linear_programming', 'integer_programming') and comp.get('x'):
            xs = [float(v) for v in comp['x']]
            labels = [f'x{i+1}' for i in range(len(xs))]
            chart_title = f'{title_prefix}最优解'[:15]
            if plt is not None:
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.bar(labels, xs, color='#10b981')
                ax.set_title(chart_title)
                ax.set_xlabel('决策变量')
                ax.set_ylabel('取值')
                ax.grid(True, axis='y', alpha=0.3)
                b64 = _fig_to_base64(fig)
                plt.close(fig)
            else:
                b64 = _simple_svg_bar(labels, xs, chart_title)
                chart_type = 'svg_bar'
        elif solver == 'monte_carlo' and comp.get('histogram'):
            counts = comp['histogram'].get('counts') or []
            edges = comp['histogram'].get('bin_edges') or []
            if counts and edges and len(edges) == len(counts) + 1:
                mids = [(edges[i] + edges[i + 1]) / 2 for i in range(len(counts))]
                chart_title = f'{title_prefix}MC分布'[:15]
                if plt is not None:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    ax.bar(mids, counts, width=(edges[1]-edges[0])*0.9, color='#8b5cf6')
                    ax.set_title(chart_title)
                    ax.set_xlabel('目标函数值')
                    ax.set_ylabel('频数')
                    ax.grid(True, alpha=0.3)
                    b64 = _fig_to_base64(fig)
                    plt.close(fig)
                else:
                    labels = [f'{m:.1f}' for m in mids[:8]]
                    b64 = _simple_svg_bar(labels, [float(c) for c in counts[:8]], chart_title)
                    chart_type = 'svg_bar'
        elif comp.get('computed') and isinstance(comp.get('computed'), dict):
            inner = comp['computed']
            if inner.get('param_mean') is not None:
                chart_title = f'{title_prefix}参数统计'[:15]
                labels = ['均值', '最小', '最大']
                vals = [float(inner.get('param_mean', 0)), float(inner.get('param_min', 0)), float(inner.get('param_max', 0))]
                if plt is not None:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    ax.bar(labels, vals, color='#6366f1')
                    ax.set_title(chart_title)
                    ax.grid(True, axis='y', alpha=0.3)
                    b64 = _fig_to_base64(fig)
                    plt.close(fig)
                else:
                    b64 = _simple_svg_bar(labels, vals, chart_title)
                    chart_type = 'svg_bar'
    except Exception as chart_err:
        charts.append({'title': f'{title_prefix}图表', 'type': solver, 'error': str(chart_err)})
        continue

    if b64:
        fig_no += 1
        cap = chart_title or f'问{idx}结果图'
        charts.append({'title': cap, 'type': chart_type, 'base64': b64, 'figure_no': fig_no})
        if chart_type == 'svg_bar':
            md = f'![图 {fig_no}：{cap}](data:image/svg+xml;base64,{b64})'
        else:
            md = f'![图 {fig_no}：{cap}](data:image/png;base64,{b64})'
        markdown_embeds.append(md)

output = {
    'charts': [{'title': c.get('title'), 'type': c.get('type'), 'has_image': bool(c.get('base64')), 'figure_no': c.get('figure_no')} for c in charts],
    'chart_images': charts,
    'markdown_embeds': markdown_embeds,
    'count': len(charts),
    'text': json.dumps({'chart_count': len(charts), 'markdown_embeds': markdown_embeds}, ensure_ascii=False),
}
'''


_TABLE_FIGURE_CODE = r'''
import json
import re

raw = input if isinstance(input, dict) else {}
if isinstance(raw.get('input'), dict) and 'node_outputs' in raw['input']:
    raw = raw['input']
nos = raw.get('node_outputs') if isinstance(raw.get('node_outputs'), dict) else {}


def _parse_obj(text):
    if not isinstance(text, str) or '{' not in text:
        return None
    s = text.strip().strip('`').replace('```json', '').replace('```', '')
    try:
        return json.loads(s[s.find('{'):s.rfind('}') + 1])
    except Exception:
        m = re.search(r'\{.*\}', s, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


sub_results = []
for out in nos.values():
    if not isinstance(out, dict):
        continue
    obj = _parse_obj(out.get('text') or '')
    if isinstance(obj, dict) and isinstance(obj.get('subproblem_results'), list):
        sub_results = obj['subproblem_results']
        break
    if isinstance(obj, dict) and obj.get('subproblem_index') is not None:
        sub_results.append(obj)

tables = []
summary_lines = ['# 结果汇总表', '', '**表 1 子问题求解汇总**', '']

rows = []
for item in sorted(sub_results, key=lambda x: int(x.get('subproblem_index') or 0)):
    idx = item.get('subproblem_index')
    comp = item.get('computed') if isinstance(item.get('computed'), dict) else {}
    st = comp.get('solver') or item.get('solver_type') or '-'
    ov = comp.get('objective_value')
    if ov is None and isinstance(comp.get('computed'), dict):
        ov = comp['computed'].get('param_mean')
    ov_s = f'{ov:.4g}' if isinstance(ov, (int, float)) else str(ov or '-')
    r2 = comp.get('r_squared')
    extra = f'R²={r2:.4f}' if isinstance(r2, (int, float)) else ''
    rows.append((idx, st, ov_s, extra, item.get('status') or 'ok'))

if rows:
    summary_lines.extend([
        '| 子问题 | 求解类型 | 目标值/指标 | 备注 | 状态 |',
        '|---|---|---|---|---|',
    ])
    for idx, st, ov, extra, status in rows:
        summary_lines.append(f'| 问{idx} | {st} | {ov} | {extra} | {status} |')
    summary_lines.append('')

table_no = 1
for item in sorted(sub_results, key=lambda x: int(x.get('subproblem_index') or 0)):
    idx = item.get('subproblem_index')
    comp = item.get('computed') if isinstance(item.get('computed'), dict) else {}
    table_no += 1
    name = f'TABLE_subproblem_{idx}.md'
    lines = [f'**表 {table_no} 问{idx} 数值结果**', '']
    if comp.get('x'):
        xs = comp['x']
        lines.extend(['| 变量 | 最优值 |', '|---|---|'])
        for i, v in enumerate(xs):
            lines.append(f'| x{i+1} | {v} |')
    elif comp.get('fitted') and comp.get('y'):
        lines.extend(['| 序号 | 观测值 | 拟合值 |', '|---|---|---|'])
        for i, (a, b) in enumerate(zip(comp['y'], comp['fitted'])):
            lines.append(f'| {i+1} | {a} | {b} |')
    elif comp.get('forecast') and comp.get('series'):
        lines.extend(['| 时间步 | 类型 | 数值 |', '|---|---|---|'])
        for i, v in enumerate(comp['series']):
            lines.append(f'| {i+1} | 历史 | {v} |')
        base = len(comp['series'])
        for i, v in enumerate(comp['forecast']):
            lines.append(f'| {base + i + 1} | 预测 | {v} |')
    elif comp.get('percentiles'):
        lines.extend(['| 分位数 | 目标值 |', '|---|---|'])
        for k, v in comp['percentiles'].items():
            lines.append(f'| P{k} | {v} |')
    elif isinstance(comp.get('computed'), dict) and comp['computed']:
        inner = comp['computed']
        lines.extend(['| 指标 | 数值 |', '|---|---|'])
        for k, v in inner.items():
            if isinstance(v, (int, float, str)):
                lines.append(f'| {k} | {v} |')
    else:
        lines.append('| 字段 | 值 |')
        lines.append('|---|---|')
        lines.append(f'| solver | {comp.get("solver", "-")} |')
    body = '\n'.join(lines)
    tables.append({'name': name, 'content': body, 'subproblem_index': idx})

summary_md = '\n'.join(summary_lines)
output = {
    'tables': tables,
    'table_markdown': summary_md,
    'table_count': len(tables) + 1,
    'text': json.dumps({'table_markdown': summary_md, 'tables': [t['name'] for t in tables]}, ensure_ascii=False),
}
'''