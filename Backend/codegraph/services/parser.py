"""
Code Parser - 多语言代码依赖解析器
支持解析 Vue, JavaScript, TypeScript, Python 等文件的 import 语句
"""

import os
import re
import ast
import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
import hashlib


@dataclass
class FileNode:
    """文件节点"""
    id: str
    path: str
    name: str
    extension: str
    size: int
    lines: int
    module: str
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    content_hash: str = ""
    functions: List['FuncNode'] = field(default_factory=list)  # 文件内函数列表

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'path': self.path,
            'name': self.name,
            'type': self.extension.lstrip('.'),
            'module': self.module,
            'size': self.size,
            'lines': self.lines,
            'imports': self.imports,
            'imported_by': self.imported_by,
            'functions': [f.to_dict() for f in self.functions],
        }


@dataclass
class FuncNode:
    """函数节点（属于某个文件节点内部）"""
    id: str  # file_node_id::funcName
    name: str
    signature: str = ""
    lineno: int = 0
    end_lineno: int = 0
    calls: List[str] = field(default_factory=list)  # 调用的函数名列表

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'signature': self.signature,
            'lineno': self.lineno,
            'end_lineno': self.end_lineno,
            'calls': self.calls,
        }


@dataclass
class DependencyEdge:
    """依赖边（文件间）"""
    id: str
    source: str
    target: str
    edge_type: str  # import, require, re-export, relative
    weight: int = 1

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'source': self.source,
            'target': self.target,
            'type': self.edge_type,
            'weight': self.weight,
        }


@dataclass
class FuncCallEdge:
    """函数调用边（文件内或跨文件）"""
    id: str
    source: str  # func_id
    target: str  # func_id
    weight: int = 1

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'source': self.source,
            'target': self.target,
            'weight': self.weight,
        }


@dataclass
class CodeStructure:
    """代码结构"""
    root_path: str
    nodes: List[FileNode] = field(default_factory=list)
    edges: List[DependencyEdge] = field(default_factory=list)
    func_nodes: List[FuncNode] = field(default_factory=list)
    func_edges: List[FuncCallEdge] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'root_path': self.root_path,
            'nodes': [n.to_dict() for n in self.nodes],
            'edges': [e.to_dict() for e in self.edges],
            'func_nodes': [f.to_dict() for f in self.func_nodes],
            'func_edges': [fe.to_dict() for fe in self.func_edges],
            'stats': self.stats,
        }


class BaseParser:
    """基础解析器"""

    IMPORT_PATTERN: re.Pattern = None

    def extract_imports(self, content: str) -> List[str]:
        if not self.IMPORT_PATTERN:
            return []
        return self.IMPORT_PATTERN.findall(content)

    def normalize_import(self, import_path: str) -> str:
        return import_path.strip("'\"")


class VueParser(BaseParser):
    """Vue 单文件组件解析器"""

    SCRIPT_PATTERN = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
    TS_SCRIPT_PATTERN = re.compile(r'<script[^>]*ts[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
    SETUP_PATTERN = re.compile(r'<script[^>]*setup[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)

    # Vue/TS import: import X from 'path' | import { X } from 'path' | import * as X from 'path'
    IMPORT_REGEX = re.compile(
        r'''import\s+(?:(?:[\w*{}\s,]+\s+from\s+)?['"]([^'"]+)['"]|[\w*{}\s,]+\s*,\s*\{[^}]*\}\s*from\s*['"]([^'"]+)['"])'''
    )
    # DYNAMIC_IMPORT: () => import('path') | import('path')
    DYNAMIC_IMPORT = re.compile(r'''import\s*\(\s*['"]([^'"]+)['"]\s*\)''')

    def extract_script_content(self, content: str) -> str:
        scripts = []
        for match in self.SCRIPT_PATTERN.finditer(content):
            scripts.append(match.group(1))
        return '\n'.join(scripts)

    def extract_imports(self, content: str) -> List[str]:
        imports = []
        script_content = self.extract_script_content(content)
        if script_content:
            for match in self.IMPORT_REGEX.finditer(script_content):
                path = match.group(1) or match.group(2)
                if path:
                    imports.append(path)
            for match in self.DYNAMIC_IMPORT.finditer(script_content):
                imports.append(match.group(1))
        return imports


class JavaScriptParser(BaseParser):
    """JavaScript/TypeScript 解析器"""

    # ES6 import
    IMPORT_REGEX = re.compile(
        r'''import\s+(?:(?:[\w*{}\s,]+\s+from\s+)?['"]([^'"]+)['"]|[\w*{}\s,]+\s*,\s*\{[^}]*\}\s*from\s*['"]([^'"]+)['"])'''
    )
    # require()
    REQUIRE_REGEX = re.compile(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)''')
    # dynamic import
    DYNAMIC_IMPORT = re.compile(r'''import\s*\(\s*['"]([^'"]+)['"]\s*\)''')
    # export from
    EXPORT_FROM_REGEX = re.compile(r'''export\s+\{[^}]+\}\s+from\s+['"]([^'"]+)['"]''')
    # export * from
    EXPORT_ALL_REGEX = re.compile(r'''export\s+\*\s+from\s+['"]([^'"]+)['"]''')

    def extract_imports(self, content: str) -> List[str]:
        imports = []

        for match in self.IMPORT_REGEX.finditer(content):
            path = match.group(1) or match.group(2)
            if path:
                imports.append(path)

        for match in self.REQUIRE_REGEX.finditer(content):
            imports.append(match.group(1))

        for match in self.DYNAMIC_IMPORT.finditer(content):
            imports.append(match.group(1))

        for match in self.EXPORT_FROM_REGEX.finditer(content):
            imports.append(match.group(1))

        for match in self.EXPORT_ALL_REGEX.finditer(content):
            imports.append(match.group(1))

        return imports


class PythonParser(BaseParser):
    """Python 解析器"""

    # import X | import X as Y
    IMPORT_REGEX = re.compile(r'''^import\s+([\w.]+)''', re.MULTILINE)
    # from X import Y | from X import Y as Z
    FROM_IMPORT_REGEX = re.compile(r'''from\s+([\w.]+)\s+import''', re.MULTILINE)

    def extract_imports(self, content: str) -> List[str]:
        imports = []

        for match in self.IMPORT_REGEX.finditer(content):
            imports.append(match.group(1))

        for match in self.FROM_IMPORT_REGEX.finditer(content):
            imports.append(match.group(1))

        return imports


class PythonFuncExtractor:
    """Python AST 函数提取器"""

    BUILTINS = {
        'print', 'len', 'range', 'str', 'int', 'float', 'bool', 'list',
        'dict', 'set', 'tuple', 'open', 'file', 'input', 'map', 'filter',
        'zip', 'enumerate', 'sorted', 'reversed', 'sum', 'min', 'max',
        'abs', 'round', 'isinstance', 'hasattr', 'getattr', 'setattr',
        'delattr', 'callable', 'type', 'id', 'hash', 'repr', 'format',
        'divmod', 'pow', 'hex', 'oct', 'bin', 'chr', 'ord', 'slice',
        'super', 'property', 'classmethod', 'staticmethod', 'vars',
        'dir', 'locals', 'globals', 'compile', 'eval', 'exec',
        'any', 'all', 'iter', 'next', 'object', 'Exception',
    }

    def extract(self, content: str, file_node_id: str) -> Tuple[List[FuncNode], List[FuncCallEdge]]:
        """提取函数节点和调用边"""
        try:
            tree = ast.parse(content)
        except (SyntaxError, ValueError):
            return [], []

        local_funcs: Set[str] = set()  # 本地定义的函数名
        imported_names: Set[str] = set()  # 导入的名字（可能是模块或函数）
        imported_modules: Set[str] = set()  # 导入的模块名
        func_nodes: List[FuncNode] = []
        call_edges: List[FuncCallEdge] = []
        edge_id = 0

        # 第一遍：收集 import 信息和函数签名
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_modules.add(node.module.split('.')[0])
                for alias in node.names:
                    if alias.asname:
                        imported_names.add(alias.asname)
                    else:
                        imported_names.add(alias.name)

        # 第二遍：收集本地函数名
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local_funcs.add(node.name)

        # 第三遍：为每个函数创建节点 + 提取调用边
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_id = f"{file_node_id}::{node.name}"
                signature = self._get_signature(node)
                calls = self._extract_calls(node, local_funcs, imported_names, imported_modules)

                func_nodes.append(FuncNode(
                    id=func_id,
                    name=node.name,
                    signature=signature,
                    lineno=node.lineno or 0,
                    end_lineno=node.end_lineno or 0,
                    calls=calls,
                ))

                for callee in calls:
                    # 查找被调用的本地函数
                    if callee in local_funcs:
                        target_id = f"{file_node_id}::{callee}"
                        call_edges.append(FuncCallEdge(
                            id=f"func_edge_{edge_id}",
                            source=func_id,
                            target=target_id,
                        ))
                        edge_id += 1

        return func_nodes, call_edges

    def _get_signature(self, node: ast.FunctionDef) -> str:
        try:
            return ast.unparse(node.args)
        except Exception:
            args = [a.arg for a in node.args.args]
            return f"({', '.join(args)})"

    def _extract_calls(
        self,
        node: ast.FunctionDef,
        local_funcs: Set[str],
        imported_names: Set[str],
        imported_modules: Set[str]
    ) -> List[str]:
        """提取函数体内的所有被调用函数名"""
        calls = []
        seen = set()

        class CallVisitor(ast.NodeVisitor):
            def visit_Call(self, call_node):
                # 获取被调用的名字
                name = None
                if isinstance(call_node.func, ast.Name):
                    name = call_node.func.id
                elif isinstance(call_node.func, ast.Attribute):
                    if isinstance(call_node.func.value, ast.Name):
                        name = call_node.func.attr  # module.attr 形式只看 attr

                if name and name not in self.builtins and name not in seen:
                    seen.add(name)
                    calls.append(name)

                self.generic_visit(call_node)

        visitor = CallVisitor()
        visitor.builtins = self.BUILTINS
        visitor.seen = seen
        visitor.calls = calls
        try:
            visitor.visit(node)
        except Exception:
            pass

        return calls


class JavaScriptFuncExtractor:
    """JavaScript 正则函数提取器（用于 JS/TS/Vue 文件）"""

    # 匹配函数声明: function name(...) { ... }  或 async function name(...) { ... }
    FUNC_DECL = re.compile(
        r'(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
        re.MULTILINE
    )
    # 匹配箭头函数: const/let/var name = (...) => ... 或 async (...) => ...
    ARROW_FUNC = re.compile(
        r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',
        re.MULTILINE
    )
    # 匹配方法: name(...) { ... }  在 class 或对象字面量中
    METHOD_DEF = re.compile(
        r'(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*(?:{|=>)',
        re.MULTILINE
    )
    # 匹配函数调用: func(...)  |  obj.func(...)
    CALL_EXPR = re.compile(
        r'(?<![.\w])(\w+)\s*\(',
        re.MULTILINE
    )

    # 内置方法（不视为本地调用）
    BUILTINS = {
        'console', 'log', 'warn', 'error', 'debug', 'info',
        'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
        'setImmediate', 'queueMicrotask',
        'setState', 'useState', 'useEffect', 'useRef', 'useMemo', 'useCallback',
        'watch', 'computed', 'ref', 'reactive', 'onMounted', 'onUnmounted',
        'fetch', 'axios', 'XMLHttpRequest',
        'JSON', 'Math', 'Date', 'RegExp', 'Array', 'Object', 'String', 'Number',
        'Boolean', 'Symbol', 'Promise', 'Map', 'Set', 'WeakMap', 'WeakSet',
        'Error', 'TypeError', 'ReferenceError', 'SyntaxError',
        'parseInt', 'parseFloat', 'isNaN', 'isFinite',
        'encodeURI', 'decodeURI', 'encodeURIComponent', 'decodeURIComponent',
        'btoa', 'atob', 'structuredClone',
        'document', 'window', 'navigator', 'location', 'history', 'localStorage',
        'sessionStorage', 'indexedDB', 'crypto', 'performance', 'requestAnimationFrame',
        'defineComponent', 'h', 'createElement', 'nextTick', 'toRaw',
        'getCurrentInstance', 'provide', 'inject', 'markRaw',
        'call', 'apply', 'bind',
    }

    def extract(self, content: str, file_node_id: str) -> Tuple[List[FuncNode], List[FuncCallEdge]]:
        """提取 JS 函数节点和调用边"""
        script = self._extract_script(content)
        if not script:
            return [], []

        func_defs = {}  # name -> (lineno, signature)
        edge_id = 0
        func_nodes: List[FuncNode] = []
        call_edges: List[FuncCallEdge] = []

        for m in self.FUNC_DECL.finditer(script):
            name, params = m.group(1), m.group(2)
            func_defs[name] = (m.start(), f"({params})")

        for m in self.ARROW_FUNC.finditer(script):
            name = m.group(1)
            func_defs[name] = (m.start(), "()")

        # 提取所有调用
        all_calls = {}
        for m in self.CALL_EXPR.finditer(script):
            name = m.group(1)
            if name not in self.BUILTINS and name not in all_calls:
                all_calls[name] = m.start()

        # 为本地定义的函数创建节点
        local_func_names = set(func_defs.keys())
        for name, (pos, sig) in func_defs.items():
            func_id = f"{file_node_id}::{name}"
            func_nodes.append(FuncNode(
                id=func_id,
                name=name,
                signature=sig,
                lineno=pos,
                end_lineno=0,
                calls=[],
            ))

        # 跨文件调用边：本地函数调用其他本地函数
        for node in func_nodes:
            called_locals = [c for c in all_calls if c in local_func_names and c != node.name]
            for callee in called_locals:
                call_edges.append(FuncCallEdge(
                    id=f"func_edge_{edge_id}",
                    source=node.id,
                    target=f"{file_node_id}::{callee}",
                ))
                edge_id += 1

        return func_nodes, call_edges

    def _extract_script(self, content: str) -> str:
        """从 Vue 文件中提取 <script> 内容"""
        match = re.search(r'<script[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE)
        return match.group(1) if match else content


class CodeParser:
    """
    代码解析器 - 统一入口
    支持多语言文件解析和依赖关系构建
    """

    # 支持的扩展名与解析器映射
    PARSERS: Dict[str, BaseParser] = {
        '.vue': VueParser(),
        '.js': JavaScriptParser(),
        '.ts': JavaScriptParser(),
        '.jsx': JavaScriptParser(),
        '.tsx': JavaScriptParser(),
        '.mjs': JavaScriptParser(),
        '.cjs': JavaScriptParser(),
        '.py': PythonParser(),
    }

    # 需要排除的目录
    EXCLUDE_DIRS: Set[str] = {
        'node_modules', '.git', '__pycache__', '.venv', 'venv',
        '.idea', '.vscode', 'dist', 'build', '.next', '.nuxt',
        'coverage', '.pytest_cache', '.mypy_cache', '.tox',
        '*.min.js', '*.bundle.js',
    }

    # 需要排除的文件
    EXCLUDE_FILES: Set[str] = {
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
        'poetry.lock', 'requirements.txt', 'Pipfile',
    }

    # 第三方库前缀（用于过滤）
    THIRD_PARTY_PREFIXES: Tuple[str, ...] = (
        'vue', '@vue', 'react', '@react', 'angular', '@angular',
        'element-plus', '@element-plus', 'ant-design', '@ant-design',
        'lodash', 'lodash-es', '_', 'rxjs', 'axios', 'echarts',
        'dayjs', 'pinia', 'vue-router', '@vue-flow',
        'django', 'django-', 'rest_framework', 'drf-',
        'channels', 'channels_redis',
    )

    def __init__(self, max_depth: int = 10, max_workers: int = 4):
        self.max_depth = max_depth
        self.max_workers = max_workers
        self._file_cache: Dict[str, FileNode] = {}
        self._path_to_id: Dict[str, str] = {}

    def _should_exclude_dir(self, dir_name: str) -> bool:
        return dir_name in self.EXCLUDE_DIRS or dir_name.startswith('.')

    def _should_exclude_file(self, file_name: str) -> bool:
        return (
            file_name in self.EXCLUDE_FILES or
            file_name.endswith('.min.js') or
            file_name.endswith('.min.css')
        )

    def _is_third_party(self, import_path: str) -> bool:
        if import_path.startswith('.'):
            return False
        for prefix in self.THIRD_PARTY_PREFIXES:
            if import_path == prefix or import_path.startswith(f'{prefix}/'):
                return True
        return False

    def _get_file_id(self, file_path: str, root_path: str) -> str:
        rel_path = os.path.relpath(file_path, root_path)
        return hashlib.md5(rel_path.encode()).hexdigest()[:12]

    def _resolve_import_path(
        self,
        import_path: str,
        current_file: str,
        root_path: str
    ) -> Optional[str]:
        """
        解析 import 路径为实际文件路径
        """
        # 跳过第三方库
        if self._is_third_party(import_path):
            return None

        current_dir = os.path.dirname(current_file)

        # 相对路径
        if import_path.startswith('.'):
            resolved = os.path.normpath(os.path.join(current_dir, import_path))
            # 处理扩展名
            for ext in ['', '.js', '.ts', '.vue', '.jsx', '.tsx', '/index.js', '/index.ts', '/index.vue']:
                if os.path.exists(resolved + ext):
                    return resolved + ext
                if os.path.isdir(resolved + ext.replace('/index', '')):
                    index_path = os.path.join(resolved + ext.replace('/index', ''), 'index.js')
                    if os.path.exists(index_path):
                        return index_path
            if os.path.exists(resolved):
                return resolved
            return None

        # 绝对路径 / 别名路径
        if import_path.startswith('@/') or import_path.startswith('@'):
            alias_path = import_path.lstrip('@/').lstrip('@')
            resolved = os.path.join(root_path, alias_path)
            for ext in ['.js', '.ts', '.vue', '.jsx', '.tsx']:
                if os.path.exists(resolved + ext):
                    return resolved + ext
            if os.path.exists(resolved):
                return resolved

        return None

    def _parse_file(self, file_path: str, root_path: str) -> Optional[FileNode]:
        """解析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            stat = os.stat(file_path)
            ext = os.path.splitext(file_path)[1].lower()

            rel_path = os.path.relpath(file_path, root_path)
            parts = rel_path.split(os.sep)

            # 模块层级 (src 下的第一层目录)
            if 'src' in parts:
                src_index = parts.index('src')
                if len(parts) > src_index + 1:
                    module = parts[src_index + 1]
                else:
                    module = 'root'
            else:
                module = parts[0] if parts else 'root'

            parser = self.PARSERS.get(ext)
            imports = parser.extract_imports(content) if parser else []

            # 解析 import 路径为实际文件
            resolved_imports = []
            for imp in imports:
                resolved = self._resolve_import_path(imp, file_path, root_path)
                if resolved:
                    resolved_imports.append(resolved)

            content_hash = hashlib.md5(content.encode()).hexdigest()[:16]

            return FileNode(
                id=self._get_file_id(file_path, root_path),
                path=rel_path,
                name=os.path.basename(file_path),
                extension=ext,
                size=stat.st_size,
                lines=len(content.splitlines()),
                module=module,
                imports=resolved_imports,
                content_hash=content_hash,
            )

        except Exception:
            return None

    def _scan_directory(self, root_path: str) -> List[str]:
        """扫描目录获取所有支持的文件"""
        files = []
        for dirpath, dirnames, filenames in os.walk(root_path):
            # 过滤目录
            dirnames[:] = [d for d in dirnames if not self._should_exclude_dir(d)]

            for filename in filenames:
                if self._should_exclude_file(filename):
                    continue
                ext = os.path.splitext(filename)[1].lower()
                if ext in self.PARSERS:
                    files.append(os.path.join(dirpath, filename))

        return files

    def build_structure(self, root_path: str) -> CodeStructure:
        """
        构建代码结构
        1. 扫描所有支持的文件
        2. 解析每个文件的依赖
        3. 提取函数节点和调用边
        4. 构建节点和边
        """
        if not os.path.exists(root_path):
            raise FileNotFoundError(f"Path not found: {root_path}")

        root_path = os.path.abspath(root_path)
        structure = CodeStructure(root_path=root_path)

        # 扫描文件
        files = self._scan_directory(root_path)

        # 并行解析文件（同时提取函数节点）
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(
                lambda f: self._parse_file(f, root_path),
                files
            ))

        # 收集节点并建立 path -> id 映射
        nodes = [r for r in results if r is not None]
        for node in nodes:
            self._file_cache[node.path] = node
            self._path_to_id[node.path] = node.id

        # 建立 imported_by 反向引用
        for node in nodes:
            for imp_path in node.imports:
                imp_rel = os.path.relpath(imp_path, root_path)
                if imp_rel in self._path_to_id:
                    target_id = self._path_to_id[imp_rel]
                    if imp_rel in self._file_cache:
                        if target_id not in self._file_cache[imp_rel].imported_by:
                            self._file_cache[imp_rel].imported_by.append(node.id)

        # 构建文件间依赖边
        edges = []
        edge_id = 0
        for node in nodes:
            for imp_path in node.imports:
                imp_rel = os.path.relpath(imp_path, root_path)
                if imp_rel in self._path_to_id:
                    edges.append(DependencyEdge(
                        id=f"edge_{edge_id}",
                        source=node.id,
                        target=self._path_to_id[imp_rel],
                        edge_type="import",
                        weight=1,
                    ))
                    edge_id += 1

        # 提取函数节点和调用边
        func_nodes = []
        func_edges = []
        py_extractor = PythonFuncExtractor()
        js_extractor = JavaScriptFuncExtractor()

        for node in nodes:
            if node.extension == '.py':
                fn, fe = py_extractor.extract(node.path, node.id)
            elif node.extension in ('.js', '.ts', '.jsx', '.tsx', '.vue', '.mjs', '.cjs'):
                fn, fe = js_extractor.extract(node.path, node.id)
            else:
                fn, fe = [], []

            node.functions.extend(fn)
            func_nodes.extend(fn)
            func_edges.extend(fe)

        structure.nodes = nodes
        structure.edges = edges
        structure.func_nodes = func_nodes
        structure.func_edges = func_edges
        structure.stats = self._compute_stats(nodes, edges, func_nodes)

        return structure

    def _compute_stats(self, nodes: List[FileNode], edges: List[DependencyEdge], func_nodes: List[FuncNode] = None) -> Dict:
        """计算统计信息"""
        type_count = {}
        module_count = {}
        total_lines = 0
        total_size = 0
        total_functions = 0

        for node in nodes:
            ext = node.extension.lstrip('.')
            type_count[ext] = type_count.get(ext, 0) + 1
            module_count[node.module] = module_count.get(node.module, 0) + 1
            total_lines += node.lines
            total_size += node.size
            total_functions += len(node.functions)

        return {
            'total_files': len(nodes),
            'total_edges': len(edges),
            'total_lines': total_lines,
            'total_size': total_size,
            'total_functions': total_functions,
            'by_type': type_count,
            'by_module': module_count,
        }

    def get_file_content(self, file_path: str) -> Optional[str]:
        """获取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None
