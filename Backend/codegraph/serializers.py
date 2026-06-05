"""
Serializers for codegraph app.
"""

from rest_framework import serializers


class ProjectSerializer(serializers.Serializer):
    """Serializer for CodeGraph project."""
    
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=200)
    path = serializers.CharField(max_length=500)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)
    last_analyzed = serializers.DateTimeField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ProjectCreateSerializer(serializers.Serializer):
    """Serializer for creating a CodeGraph project."""
    
    name = serializers.CharField(max_length=200)
    path = serializers.CharField(max_length=500)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate_path(self, value):
        """Validate that the path exists."""
        import os
        if not os.path.exists(value):
            raise serializers.ValidationError(f"Path does not exist: {value}")
        return value


class FileNodeSerializer(serializers.Serializer):
    """Serializer for file node."""
    
    id = serializers.CharField()
    path = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    module = serializers.CharField()
    size = serializers.IntegerField()
    lines = serializers.IntegerField()
    imports = serializers.ListField(child=serializers.CharField(), required=False)
    imported_by = serializers.ListField(child=serializers.CharField(), required=False)
    indegree = serializers.IntegerField(default=0)
    outdegree = serializers.IntegerField(default=0)
    centrality = serializers.FloatField(default=0.0)
    depth = serializers.IntegerField(default=0)


class DependencyEdgeSerializer(serializers.Serializer):
    """Serializer for dependency edge."""
    
    id = serializers.CharField()
    source = serializers.CharField()
    target = serializers.CharField()
    type = serializers.CharField()
    weight = serializers.IntegerField(default=1)


class GraphStatsSerializer(serializers.Serializer):
    """Serializer for graph statistics."""
    
    total_files = serializers.IntegerField()
    total_edges = serializers.IntegerField()
    total_lines = serializers.IntegerField()
    total_size = serializers.IntegerField()
    by_type = serializers.DictField(child=serializers.IntegerField())
    by_module = serializers.DictField(child=serializers.IntegerField())


class CycleSerializer(serializers.Serializer):
    """Serializer for cycle detection result."""
    
    nodes = serializers.ListField(child=serializers.CharField())
    length = serializers.IntegerField()


class HotspotSerializer(serializers.Serializer):
    """Serializer for code hotspot."""
    
    id = serializers.CharField()
    path = serializers.CharField()
    name = serializers.CharField()
    score = serializers.FloatField()
    centrality = serializers.FloatField()
    indegree = serializers.IntegerField()
    outdegree = serializers.IntegerField()


class GraphDataSerializer(serializers.Serializer):
    """Serializer for complete graph data."""
    
    project_id = serializers.IntegerField()
    project_name = serializers.CharField()
    project_path = serializers.CharField()
    nodes = FileNodeSerializer(many=True)
    edges = DependencyEdgeSerializer(many=True)
    stats = GraphStatsSerializer()
    cycles = CycleSerializer(many=True, required=False)
    hotspots = HotspotSerializer(many=True, required=False)
    last_updated = serializers.CharField(required=False)


class SearchQuerySerializer(serializers.Serializer):
    """Serializer for search query."""
    
    q = serializers.CharField(required=True)
    type = serializers.ChoiceField(
        choices=['file', 'module', 'all'],
        default='all'
    )
    module = serializers.CharField(required=False)
    limit = serializers.IntegerField(default=20, min_value=1, max_value=100)


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search result."""
    
    id = serializers.CharField()
    path = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    module = serializers.CharField()
    match_type = serializers.CharField()  # name, path, content


class FileContentSerializer(serializers.Serializer):
    """Serializer for file content."""
    
    path = serializers.CharField()
    name = serializers.CharField()
    extension = serializers.CharField()
    size = serializers.IntegerField()
    lines = serializers.IntegerField()
    content = serializers.CharField()
    highlighted_content = serializers.CharField(required=False)


class ModuleDependencySerializer(serializers.Serializer):
    """Serializer for module dependency."""
    
    source_module = serializers.CharField()
    target_module = serializers.CharField()
    file_count = serializers.IntegerField()


class AnalysisRequestSerializer(serializers.Serializer):
    """Serializer for analysis request."""
    
    force_refresh = serializers.BooleanField(default=False)
    include_cycles = serializers.BooleanField(default=True)
    include_hotspots = serializers.BooleanField(default=True)
