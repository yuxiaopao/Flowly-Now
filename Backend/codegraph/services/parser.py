"""
Code Parser - 多语言代码依赖解析器
支持解析 Vue, JavaScript, TypeScript, Python 等文件的 import 语句
"""

import os
import re
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
        }


@dataclass
class DependencyEdge:
    """依赖边"""
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
class CodeStructure:
    """代码结构"""
    root_path: str
    nodes: List[FileNode] = field(default_factory=list)
    edges: List[DependencyEdge] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'root_path': self.root_path,
            'nodes': [n.to_dict() for n in self.nodes],
            'edges': [e.to_dict() for e in self.edges],
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
        3. 构建节点和边
        """
        if not os.path.exists(root_path):
            raise FileNotFoundError(f"Path not found: {root_path}")

        root_path = os.path.abspath(root_path)
        structure = CodeStructure(root_path=root_path)

        # 扫描文件
        files = self._scan_directory(root_path)

        # 并行解析文件
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
                    if node.id in self._file_cache:
                        if target_id not in self._file_cache[imp_rel].imported_by:
                            self._file_cache[imp_rel].imported_by.append(node.id)

        # 构建边
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

        structure.nodes = nodes
        structure.edges = edges
        structure.stats = self._compute_stats(nodes, edges)

        return structure

    def _compute_stats(self, nodes: List[FileNode], edges: List[DependencyEdge]) -> Dict:
        """计算统计信息"""
        type_count = {}
        module_count = {}
        total_lines = 0
        total_size = 0

        for node in nodes:
            ext = node.extension.lstrip('.')
            type_count[ext] = type_count.get(ext, 0) + 1
            module_count[node.module] = module_count.get(node.module, 0) + 1
            total_lines += node.lines
            total_size += node.size

        return {
            'total_files': len(nodes),
            'total_edges': len(edges),
            'total_lines': total_lines,
            'total_size': total_size,
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
