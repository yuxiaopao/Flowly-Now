"""
Workflow import/export API views.
"""

import json
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, JSONParser

from .models import Workflow
from .import_export import WorkflowExporter, WorkflowImporter


class WorkflowExportView(APIView):
    """Export workflow API."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def get(self, request, workflow_id):
        """Export workflow to JSON."""
        format_type = request.query_params.get('format', 'json')

        try:
            workflow = Workflow.objects.get(id=workflow_id, owner=request.user)
        except Workflow.DoesNotExist:
            return Response(
                {'error': 'Workflow not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        exporter = WorkflowExporter(workflow)

        if format_type == 'json':
            data = exporter.to_json()
            return Response(data)
        elif format_type == 'base64':
            data = exporter.to_base64()
            return Response({'data': data})
        else:
            return Response(
                {'error': f'Unsupported format: {format_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def post(self, request, workflow_id):
        """Export workflow as downloadable file."""
        try:
            workflow = Workflow.objects.get(id=workflow_id, owner=request.user)
        except Workflow.DoesNotExist:
            return Response(
                {'error': 'Workflow not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        exporter = WorkflowExporter(workflow)
        file_content = exporter.to_file()

        response = HttpResponse(file_content, content_type='application/zip')
        filename = f"{workflow.name.replace(' ', '_')}.flowly"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class WorkflowImportView(APIView):
    """Import workflow API."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def post(self, request):
        """Import workflow from JSON or file."""
        source = request.data.get('source', 'json')

        try:
            importer = WorkflowImporter(request.user)

            if source == 'json':
                workflow_data = request.data.get('workflow')
                if not workflow_data:
                    return Response(
                        {'error': 'workflow data is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if isinstance(workflow_data, str):
                    workflow_data = json.loads(workflow_data)

            elif source == 'file':
                uploaded_file = request.FILES.get('file')
                if not uploaded_file:
                    return Response(
                        {'error': 'file is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                workflow_data = importer.from_file(uploaded_file.read())

            elif source == 'base64':
                encoded_data = request.data.get('data')
                if not encoded_data:
                    return Response(
                        {'error': 'data is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                workflow_data = importer.from_base64(encoded_data)

            else:
                return Response(
                    {'error': f'Unsupported source: {source}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate
            validation = importer.validate(
                {'workflow': workflow_data, 'type': 'flowly_workflow'}
            )

            if not validation['valid']:
                return Response({
                    'error': 'Validation failed',
                    'details': validation['errors']
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create workflow
            workflow = Workflow.objects.create(
                name=workflow_data.get('name', 'Imported Workflow'),
                description=workflow_data.get('description', ''),
                nodes=workflow_data.get('nodes', []),
                edges=workflow_data.get('edges', []),
                variables=workflow_data.get('variables', {}),
                owner=request.user
            )

            return Response({
                'id': workflow.id,
                'name': workflow.name,
                'message': 'Workflow imported successfully',
                'validation': validation
            }, status=status.HTTP_201_CREATED)

        except json.JSONDecodeError:
            return Response(
                {'error': 'Invalid JSON format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class WorkflowValidationView(APIView):
    """Validate workflow data."""

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        """Validate workflow data."""
        workflow_data = request.data.get('workflow')

        if not workflow_data:
            return Response(
                {'error': 'workflow data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        importer = WorkflowImporter(request.user)
        validation = importer.validate({
            'workflow': workflow_data,
            'type': 'flowly_workflow'
        })

        return Response(validation)


class WorkflowDuplicateView(APIView):
    """Duplicate workflow."""

    permission_classes = [IsAuthenticated]

    def post(self, request, workflow_id):
        """Create a copy of a workflow."""
        try:
            original = Workflow.objects.get(id=workflow_id, owner=request.user)
        except Workflow.DoesNotExist:
            return Response(
                {'error': 'Workflow not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create duplicate
        duplicate = Workflow.objects.create(
            name=f"{original.name} (Copy)",
            description=original.description,
            nodes=original.nodes,
            edges=original.edges,
            variables=original.variables,
            owner=request.user
        )

        return Response({
            'id': duplicate.id,
            'name': duplicate.name,
            'message': 'Workflow duplicated successfully'
        }, status=status.HTTP_201_CREATED)
