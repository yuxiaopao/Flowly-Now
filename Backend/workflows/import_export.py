"""
Workflow import/export service.
"""

import json
import zipfile
import base64
from io import BytesIO
from typing import Optional, Dict, Any

from django.conf import settings


class WorkflowExporter:
    """Export workflow to various formats."""

    def __init__(self, workflow):
        self.workflow = workflow

    def to_json(self, include_metadata: bool = True) -> Dict[str, Any]:
        """Export workflow as JSON."""
        data = {
            'version': '1.0',
            'type': 'flowly_workflow',
            'workflow': {
                'name': self.workflow.name,
                'description': self.workflow.description,
                'nodes': self.workflow.nodes,
                'edges': self.workflow.edges,
                'variables': self.workflow.variables,
            }
        }

        if include_metadata:
            data['metadata'] = {
                'id': self.workflow.id,
                'created_at': self.workflow.created_at.isoformat() if self.workflow.created_at else None,
                'updated_at': self.workflow.updated_at.isoformat() if self.workflow.updated_at else None,
                'created_by': self.workflow.owner.username if self.workflow.owner else None,
            }

        return data

    def to_file(self, include_assets: bool = True) -> bytes:
        """
        Export workflow as a .flowly file (ZIP archive).
        Includes workflow JSON and any associated assets.
        """
        buffer = BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Main workflow JSON
            workflow_json = json.dumps(self.to_json(), indent=2, ensure_ascii=False)
            zf.writestr('workflow.json', workflow_json)

            # Manifest
            manifest = {
                'version': '1.0',
                'type': 'flowly_workflow',
                'format': 'package',
                'files': ['workflow.json']
            }
            zf.writestr('manifest.json', json.dumps(manifest, indent=2))

        buffer.seek(0)
        return buffer.read()

    def to_base64(self) -> str:
        """Export workflow as base64 encoded string."""
        return base64.b64encode(self.to_json().encode('utf-8')).decode('utf-8')


class WorkflowImporter:
    """Import workflow from various formats."""

    def __init__(self, user):
        self.user = user

    def from_json(
        self,
        data: Dict[str, Any],
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Import workflow from JSON."""
        if data.get('type') != 'flowly_workflow':
            raise ValueError("Invalid workflow format")

        workflow_data = data.get('workflow', {})

        return {
            'name': name or workflow_data.get('name', 'Imported Workflow'),
            'description': description or workflow_data.get('description', ''),
            'nodes': workflow_data.get('nodes', []),
            'edges': workflow_data.get('edges', []),
            'variables': workflow_data.get('variables', {}),
        }

    def from_file(self, file_content: bytes) -> Dict[str, Any]:
        """Import workflow from .flowly file (ZIP archive)."""
        buffer = BytesIO(file_content)

        with zipfile.ZipFile(buffer, 'r') as zf:
            # Check manifest
            if 'manifest.json' in zf.namelist():
                manifest = json.loads(zf.read('manifest.json'))
                if manifest.get('type') != 'flowly_workflow':
                    raise ValueError("Invalid package format")

            # Read workflow JSON
            if 'workflow.json' not in zf.namelist():
                raise ValueError("workflow.json not found in package")

            workflow_json = json.loads(zf.read('workflow.json'))
            return self.from_json(workflow_json)

    def from_base64(self, encoded_data: str) -> Dict[str, Any]:
        """Import workflow from base64 encoded JSON."""
        decoded = base64.b64decode(encoded_data.encode('utf-8'))
        data = json.loads(decoded)
        return self.from_json(data)

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow data and return validation result."""
        errors = []
        warnings = []

        workflow_data = data.get('workflow', {})

        # Check required fields
        if not workflow_data.get('name'):
            errors.append("Workflow name is required")

        if not workflow_data.get('nodes'):
            warnings.append("Workflow has no nodes")

        # Validate nodes
        nodes = workflow_data.get('nodes', [])
        node_ids = set()
        has_start = False
        has_end = False

        for node in nodes:
            if not isinstance(node, dict):
                errors.append(f"Invalid node format: {node}")
                continue

            node_id = node.get('id')
            if not node_id:
                errors.append("Node missing ID")
            elif node_id in node_ids:
                errors.append(f"Duplicate node ID: {node_id}")
            else:
                node_ids.add(node_id)

            node_type = node.get('type')
            if node_type == 'start':
                has_start = True
            elif node_type == 'end':
                has_end = True

        if not has_start:
            warnings.append("Workflow has no start node")
        if not has_end:
            warnings.append("Workflow has no end node")

        # Validate edges
        edges = workflow_data.get('edges', [])
        edge_connections = set()

        for edge in edges:
            if not isinstance(edge, dict):
                errors.append(f"Invalid edge format: {edge}")
                continue

            source = edge.get('source')
            target = edge.get('target')

            if not source or not target:
                errors.append(f"Edge missing source or target: {edge}")
            else:
                conn_key = f"{source}-{target}"
                if conn_key in edge_connections:
                    warnings.append(f"Duplicate edge: {source} -> {target}")
                else:
                    edge_connections.add(conn_key)

                # Check if connected nodes exist
                if source not in node_ids:
                    errors.append(f"Edge references non-existent source node: {source}")
                if target not in node_ids:
                    errors.append(f"Edge references non-existent target node: {target}")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'nodes': len(nodes),
                'edges': len(edges),
                'node_ids': len(node_ids)
            }
        }


def export_workflow(workflow, format: str = 'json') -> Any:
    """Export workflow to specified format."""
    exporter = WorkflowExporter(workflow)

    if format == 'json':
        return exporter.to_json()
    elif format == 'file':
        return exporter.to_file()
    elif format == 'base64':
        return exporter.to_base64()
    else:
        raise ValueError(f"Unsupported export format: {format}")


def import_workflow(user, data: Any, format: str = 'json') -> Dict[str, Any]:
    """Import workflow from specified format."""
    importer = WorkflowImporter(user)

    if format == 'json':
        if isinstance(data, str):
            data = json.loads(data)
        return importer.from_json(data)
    elif format == 'file':
        return importer.from_file(data)
    elif format == 'base64':
        return importer.from_base64(data)
    else:
        raise ValueError(f"Unsupported import format: {format}")
