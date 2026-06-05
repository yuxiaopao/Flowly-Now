"""
Views for codegraph app.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .services.parser import CodeParser
from .services.analyzer import GraphAnalyzer
from .services.cache import GraphCache, ProjectCache
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer,
    GraphDataSerializer, SearchQuerySerializer, SearchResultSerializer,
    FileContentSerializer, AnalysisRequestSerializer,
)

logger = logging.getLogger(__name__)

# 全局实例
_code_parser = CodeParser(max_workers=4)
_graph_analyzer = GraphAnalyzer()
_graph_cache = GraphCache()
_project_cache = ProjectCache(_graph_cache)

# 项目配置 - 可以从数据库读取
PROJECT_CONFIGS: Dict[int, dict] = {
    1: {
        'name': 'Frontend',
        'path': os.path.join(settings.BASE_DIR, '..', 'Frontend', 'src'),
    },
    2: {
        'name': 'Backend',
        'path': os.path.join(settings.BASE_DIR, '..', 'Backend'),
    },
}


def get_project_config(project_id: int) -> Optional[dict]:
    """获取项目配置"""
    return PROJECT_CONFIGS.get(project_id)


def _get_structure_for_project(project_id: int, project_path: str):
    """获取项目结构，确保返回 CodeStructure 实例。"""
    structure = _project_cache.get_structure(project_id, project_path)
    if structure is None:
        structure = _code_parser.build_structure(project_path)
        _project_cache.set_structure(project_id, structure)
    return structure


def _resolve_project_file_path(project_path: str, relative_path: str) -> Optional[str]:
    """安全解析项目内文件路径，禁止目录穿越。"""
    if not relative_path:
        return None

    normalized_relative_path = os.path.normpath(relative_path)
    if normalized_relative_path in {'.', ''}:
        return None

    base_path = os.path.realpath(project_path)
    candidate_path = os.path.realpath(os.path.join(base_path, normalized_relative_path))

    try:
        common_path = os.path.commonpath([base_path, candidate_path])
    except ValueError:
        return None

    if common_path != base_path:
        return None

    return candidate_path


def broadcast_update(project_id: int, event_type: str, data: dict):
    """广播更新到 WebSocket"""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'codegraph_{project_id}',
                {
                    'type': 'graph_update',
                    'event': event_type,
                    'data': data,
                    'timestamp': datetime.now().isoformat(),
                }
            )
    except Exception as e:
        logger.warning(f"Failed to broadcast update: {e}")


class ProjectListView(APIView):
    """项目列表 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """获取所有项目列表"""
        projects = []
        for project_id, config in PROJECT_CONFIGS.items():
            path = config.get('path', '')
            is_valid = os.path.exists(path)
            
            projects.append({
                'id': project_id,
                'name': config.get('name', f'Project {project_id}'),
                'path': path,
                'is_valid': is_valid,
                'last_analyzed': None,
            })
        
        return Response({
            'projects': projects,
            'count': len(projects),
        })


class ProjectDetailView(APIView):
    """项目详情 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id: int):
        """获取项目详情"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        path = config.get('path', '')
        is_valid = os.path.exists(path)
        
        return Response({
            'id': project_id,
            'name': config.get('name', f'Project {project_id}'),
            'path': path,
            'is_valid': is_valid,
        })


class ProjectStructureView(APIView):
    """项目代码结构 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id: int):
        """获取项目代码结构（文件树）"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        project_path = config.get('path', '')
        if not os.path.exists(project_path):
            return Response(
                {'error': 'Project path does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 尝试从缓存获取
        structure = _get_structure_for_project(project_id, project_path)
        
        return Response({
            'project_id': project_id,
            'project_name': config.get('name'),
            'root_path': project_path,
            'nodes': [n.to_dict() for n in structure.nodes],
            'stats': structure.stats,
        })


class GraphDataView(APIView):
    """依赖图数据 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id: int):
        """获取依赖图数据"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        project_path = config.get('path', '')
        project_name = config.get('name', f'Project {project_id}')
        
        if not os.path.exists(project_path):
            return Response(
                {'error': 'Project path does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 检查缓存
        force_refresh = request.query_params.get('force_refresh', 'false').lower() == 'true'
        
        if not force_refresh:
            cached_analysis = _project_cache.get_analysis(project_id)
            if cached_analysis:
                return Response(cached_analysis.to_dict())
        
        # 构建并分析
        structure = _code_parser.build_structure(project_path)
        analysis = _graph_analyzer.analyze(structure, project_id, project_name)
        
        # 缓存结果
        _project_cache.set_analysis(project_id, analysis)
        
        return Response(analysis.to_dict())


class GraphStatsView(APIView):
    """图统计 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id: int):
        """获取图统计信息"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 获取分析数据
        analysis = _project_cache.get_analysis(project_id)
        
        if analysis:
            return Response({
                'stats': analysis.stats,
                'cycles': analysis.cycles,
                'hotspots': analysis.hotspots,
                'metrics': analysis.metrics,
            })
        
        return Response({
            'error': 'Analysis not found. Please call /graph/ first.',
        }, status=status.HTTP_400_BAD_REQUEST)


class AnalyzeView(APIView):
    """重新分析 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, project_id: int):
        """触发项目重新分析"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        project_path = config.get('path', '')
        project_name = config.get('name', f'Project {project_id}')
        
        # 失效缓存
        _project_cache.invalidate(project_id)
        
        # 重新分析
        structure = _code_parser.build_structure(project_path)
        analysis = _graph_analyzer.analyze(
            structure, project_id, project_name,
        )
        
        # 缓存结果
        _project_cache.set_analysis(project_id, analysis)
        
        # 广播更新
        broadcast_update(project_id, 'full_refresh', {
            'project_id': project_id,
        })
        
        return Response({
            'message': 'Analysis completed',
            'analysis': analysis.to_dict(),
        })


class FileContentView(APIView):
    """文件内容 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id: int):
        """获取文件内容"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        file_path = request.query_params.get('path')
        if not file_path:
            return Response(
                {'error': 'path parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project_path = config.get('path', '')
        full_path = _resolve_project_file_path(project_path, file_path)

        if full_path is None:
            return Response(
                {'error': 'Invalid file path'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not os.path.exists(full_path):
            return Response(
                {'error': 'File not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        content = _code_parser.get_file_content(full_path)
        if content is None:
            return Response(
                {'error': 'Failed to read file'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        stat = os.stat(full_path)
        _, ext = os.path.splitext(file_path)
        
        return Response({
            'path': file_path,
            'name': os.path.basename(file_path),
            'extension': ext,
            'size': stat.st_size,
            'lines': len(content.splitlines()),
            'content': content,
        })


class SearchView(APIView):
    """搜索 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id: int):
        """搜索文件或模块"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['q'].lower()
        search_type = serializer.validated_data.get('type', 'all')
        module_filter = serializer.validated_data.get('module')
        limit = serializer.validated_data.get('limit', 20)
        
        # 获取结构
        project_path = config.get('path', '')
        structure = _get_structure_for_project(project_id, project_path)
        
        results = []
        for node in structure.nodes:
            # 类型过滤
            if search_type == 'file':
                if node.extension not in ['.vue', '.js', '.ts', '.jsx', '.tsx']:
                    continue
            elif search_type == 'module':
                # 模块过滤，查找顶级目录
                pass
            
            # 模块过滤
            if module_filter and node.module != module_filter:
                continue
            
            # 搜索匹配
            name_match = query in node.name.lower()
            path_match = query in node.path.lower()
            
            if name_match or path_match:
                match_type = 'name' if name_match else 'path'
                results.append({
                    'id': node.id,
                    'path': node.path,
                    'name': node.name,
                    'type': node.extension.lstrip('.'),
                    'module': node.module,
                    'match_type': match_type,
                })
                
                if len(results) >= limit:
                    break
        
        return Response({
            'query': query,
            'results': results,
            'count': len(results),
        })


class ModuleListView(APIView):
    """模块列表 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id: int):
        """获取项目模块列表"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 获取统计
        analysis = _project_cache.get_analysis(project_id)
        
        if analysis and analysis.stats.get('by_module'):
            modules = []
            for module_name, file_count in analysis.stats['by_module'].items():
                modules.append({
                    'name': module_name,
                    'file_count': file_count,
                })
            return Response({
                'modules': modules,
                'count': len(modules),
            })
        
        return Response({
            'modules': [],
            'count': 0,
        })


class ModuleDependencyView(APIView):
    """模块依赖关系 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, project_id: int):
        """获取模块间的依赖关系"""
        config = get_project_config(project_id)
        if not config:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        project_path = config.get('path', '')
        structure = _get_structure_for_project(project_id, project_path)
        
        # 构建模块依赖
        module_deps: Dict[str, Dict[str, int]] = {}
        file_to_module: Dict[str, str] = {}
        
        for node in structure.nodes:
            file_to_module[node.id] = node.module
        
        for edge in structure.edges:
            source_module = file_to_module.get(edge.source)
            target_module = file_to_module.get(edge.target)
            
            if source_module and target_module and source_module != target_module:
                if source_module not in module_deps:
                    module_deps[source_module] = {}
                module_deps[source_module][target_module] = \
                    module_deps[source_module].get(target_module, 0) + 1
        
        # 转换为列表格式
        dependencies = []
        for source, targets in module_deps.items():
            for target, count in targets.items():
                dependencies.append({
                    'source_module': source,
                    'target_module': target,
                    'file_count': count,
                })
        
        return Response({
            'dependencies': dependencies,
            'count': len(dependencies),
        })


class CacheInvalidateView(APIView):
    """缓存失效 API"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, project_id: int):
        """失效项目缓存"""
        _project_cache.invalidate(project_id)
        
        return Response({
            'message': 'Cache invalidated',
            'project_id': project_id,
        })


# WebSocket 连接测试视图
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def ws_status(request):
    """WebSocket 连接状态"""
    return Response({
        'websocket': 'available',
        'channel_prefix': 'codegraph_',
    })
