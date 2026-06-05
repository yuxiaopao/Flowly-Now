"""
Graph Analyzer - 图结构分析与计算
计算节点中心性、检测循环依赖、找出热点模块等
"""

import os
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor

from .parser import CodeStructure, FileNode, DependencyEdge


@dataclass
class AnalysisResult:
    """分析结果"""
    project_id: int
    project_name: str
    project_path: str
    nodes: List[dict] = field(default_factory=list)
    edges: List[dict] = field(default_factory=list)
    stats: Dict = field(default_factory=dict)
    cycles: List[List[str]] = field(default_factory=list)
    hotspots: List[dict] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    last_updated: str = ""

    def to_dict(self) -> dict:
        def serialize_metric(v):
            if hasattr(v, 'to_dict'):
                return v.to_dict()
            return v
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'project_path': self.project_path,
            'nodes': self.nodes,
            'edges': self.edges,
            'stats': self.stats,
            'cycles': self.cycles,
            'hotspots': self.hotspots,
            'metrics': {k: serialize_metric(v) for k, v in self.metrics.items()} if isinstance(self.metrics, dict) else self.metrics,
            'last_updated': self.last_updated,
        }


@dataclass
class NodeMetrics:
    """节点度量"""
    id: str
    path: str
    name: str
    indegree: int = 0  # 入度 (被导入次数)
    outdegree: int = 0  # 出度 (导入次数)
    centrality: float = 0.0  # 中心性
    depth: int = 0  # 层级深度
    fan_in: int = 0  # 被依赖数
    fan_out: int = 0  # 依赖数

    def to_dict(self) -> dict:
        """转换为字典用于 JSON 序列化"""
        return {
            'id': self.id,
            'path': self.path,
            'name': self.name,
            'indegree': self.indegree,
            'outdegree': self.outdegree,
            'centrality': round(self.centrality, 4),
            'depth': self.depth,
            'fan_in': self.fan_in,
            'fan_out': self.fan_out,
        }


class GraphAnalyzer:
    """
    图结构分析器
    """

    def __init__(self):
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)  # source -> targets
        self._reverse_adjacency: Dict[str, Set[str]] = defaultdict(set)  # target -> sources
        self._nodes: Dict[str, FileNode] = {}

    def _build_adjacency(self, structure: CodeStructure):
        """构建邻接表"""
        self._adjacency.clear()
        self._reverse_adjacency.clear()
        self._nodes.clear()

        for node in structure.nodes:
            self._nodes[node.id] = node

        for edge in structure.edges:
            self._adjacency[edge.source].add(edge.target)
            self._reverse_adjacency[edge.target].add(edge.source)

    def analyze(self, structure: CodeStructure, project_id: int, project_name: str) -> AnalysisResult:
        """
        综合分析代码结构
        """
        self._build_adjacency(structure)

        # 计算各项指标
        metrics = self._calculate_all_metrics()
        cycles = self.detect_cycles()
        hotspots = self.find_hotspots()
        enriched_nodes = self._enrich_nodes(structure.nodes, metrics)

        return AnalysisResult(
            project_id=project_id,
            project_name=project_name,
            project_path=structure.root_path,
            nodes=enriched_nodes,
            edges=[e.to_dict() for e in structure.edges],
            stats=structure.stats,
            cycles=cycles,
            hotspots=hotspots,
            metrics=metrics,
            last_updated=structure.stats.get('last_updated', ''),
        )

    def _enrich_nodes(self, nodes: List[FileNode], metrics: Dict[str, NodeMetrics]) -> List[dict]:
        """为节点添加分析指标"""
        enriched = []
        for node in nodes:
            node_dict = node.to_dict()
            if node.id in metrics:
                m = metrics[node.id]
                node_dict.update({
                    'indegree': m.indegree,
                    'outdegree': m.outdegree,
                    'centrality': round(m.centrality, 4),
                    'depth': m.depth,
                    'fan_in': m.fan_in,
                    'fan_out': m.fan_out,
                })
            enriched.append(node_dict)
        return enriched

    def _calculate_all_metrics(self) -> Dict[str, NodeMetrics]:
        """计算所有节点度量"""
        metrics = {}

        # 计算入度和出度
        for node_id in self._nodes:
            node = self._nodes[node_id]
            out_degree = len(self._adjacency.get(node_id, set()))
            in_degree = len(self._reverse_adjacency.get(node_id, set()))

            metrics[node_id] = NodeMetrics(
                id=node_id,
                path=node.path,
                name=node.name,
                indegree=in_degree,
                outdegree=out_degree,
                fan_in=in_degree,
                fan_out=out_degree,
            )

        # 计算中心性 (Betweenness Centrality - 简化版)
        centrality = self._calculate_betweenness_centrality()
        for node_id, cent in centrality.items():
            if node_id in metrics:
                metrics[node_id].centrality = cent

        # 计算深度 (基于拓扑排序)
        depths = self._calculate_depths()
        for node_id, depth in depths.items():
            if node_id in metrics:
                metrics[node_id].depth = depth

        return metrics

    def _calculate_betweenness_centrality(self) -> Dict[str, float]:
        """
        计算介数中心性
        衡量节点在图中作为"桥梁"的重要性
        """
        centrality = defaultdict(float)
        nodes = list(self._nodes.keys())
        n = len(nodes)

        if n <= 1:
            return centrality

        # 对每个节点作为源计算最短路径
        for source in nodes:
            # BFS 计算从 source 到所有节点的最短路径
            distances = {source: 0}
            predecessors = defaultdict(list)
            sigma = defaultdict(float)  # 路径数量

            queue = deque([source])
            sigma[source] = 1

            while queue:
                current = queue.popleft()
                for target in self._adjacency.get(current, set()):
                    # 第一次发现
                    if target not in distances:
                        distances[target] = distances[current] + 1
                        queue.append(target)
                    # 找到最短路径
                    if distances[target] == distances[current] + 1:
                        sigma[target] += sigma[current]
                        predecessors[target].append(current)

            # 计算依赖值
            dependency = defaultdict(float)
            nodes_by_distance = sorted(distances.items(), key=lambda x: -x[1])
            for _, v in nodes_by_distance:
                for pred in predecessors.get(v, []):
                    dependency[pred] += (sigma[pred] / sigma[v]) * (1 + dependency[v])

            # 累加中心性
            if n > 2:
                for node in distances:
                    centrality[node] += dependency[node] / ((n - 1) * (n - 2))

        # 归一化
        if n > 2:
            norm = 2 / ((n - 1) * (n - 2))
            for node in centrality:
                centrality[node] *= norm

        return dict(centrality)

    def _calculate_depths(self) -> Dict[str, int]:
        """
        计算每个节点的层级深度
        基于拓扑排序，从叶子节点向上计算
        """
        depths = {}
        in_degree = {}

        # 计算入度
        for node_id in self._nodes:
            in_degree[node_id] = len(self._reverse_adjacency.get(node_id, set()))

        # 拓扑排序 (Kahn 算法)
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        level = 0

        while queue:
            next_queue = deque()
            for node_id in queue:
                depths[node_id] = level
                for target in self._adjacency.get(node_id, set()):
                    in_degree[target] -= 1
                    if in_degree[target] == 0:
                        next_queue.append(target)
            queue = next_queue
            level += 1

        # 处理不在拓扑排序中的节点（循环依赖中的节点）
        for node_id in self._nodes:
            if node_id not in depths:
                depths[node_id] = level

        return depths

    def detect_cycles(self) -> List[List[str]]:
        """
        检测循环依赖
        返回所有循环路径
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            has_cycle = False
            for neighbor in self._adjacency.get(node_id, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        has_cycle = True
                elif neighbor in rec_stack:
                    # 发现循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    has_cycle = True

            path.pop()
            rec_stack.remove(node_id)
            return has_cycle

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id)

        # 去重并简化循环
        simplified = []
        seen = set()
        for cycle in cycles:
            # 创建规范化的循环表示
            min_idx = cycle.index(min(cycle[:-1]))
            normalized = tuple(cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]])
            if normalized not in seen:
                seen.add(normalized)
                simplified.append(list(normalized))

        return simplified

    def find_hotspots(self, top_n: int = 10) -> List[dict]:
        """
        找出高耦合热点模块
        基于中心性和入度综合计算
        """
        hotspots = []
        metrics = self._calculate_all_metrics()

        for node_id, metric in metrics.items():
            # 综合得分: 60% 中心性 + 40% 入度
            score = 0.6 * metric.centrality + 0.4 * (metric.indegree / max(len(self._nodes), 1))
            hotspots.append({
                'id': node_id,
                'path': metric.path,
                'name': metric.name,
                'score': round(score, 4),
                'centrality': round(metric.centrality, 4),
                'indegree': metric.indegree,
                'outdegree': metric.outdegree,
            })

        # 按分数排序
        hotspots.sort(key=lambda x: x['score'], reverse=True)
        return hotspots[:top_n]

    def get_module_dependencies(self) -> Dict[str, List[str]]:
        """
        获取模块间的依赖关系
        按模块聚合文件依赖
        """
        module_deps = defaultdict(set)
        file_to_module = {}

        for node in self._nodes.values():
            file_to_module[node.id] = node.module

        for source_id, targets in self._adjacency.items():
            source_module = file_to_module.get(source_id)
            if not source_module:
                continue
            for target_id in targets:
                target_module = file_to_module.get(target_id)
                if target_module and source_module != target_module:
                    module_deps[source_module].add(target_module)

        return {k: list(v) for k, v in module_deps.items()}

    def suggest_decomposition(self) -> List[dict]:
        """
        建议模块拆分
        基于高内聚低耦合原则
        """
        module_files = defaultdict(list)
        for node in self._nodes.values():
            module_files[node.module].append(node)

        suggestions = []
        for module, files in module_files.items():
            if len(files) > 20:  # 文件过多，建议拆分
                suggestions.append({
                    'module': module,
                    'file_count': len(files),
                    'reason': f'Module "{module}" has {len(files)} files, consider decomposition',
                    'priority': 'high' if len(files) > 30 else 'medium',
                })

        return sorted(suggestions, key=lambda x: x['file_count'], reverse=True)
