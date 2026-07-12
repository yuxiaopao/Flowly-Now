"""
Views for datasets app.
"""

import os
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q

from .models import Dataset
from .serializers import (
    DatasetSerializer, DatasetListSerializer,
    DatasetCreateSerializer, DatasetUpdateSerializer,
    DatasetPreviewSerializer, DatasetStatsSerializer
)
from .utils import (
    detect_format_from_extension, parse_dataset_file,
    detect_columns_and_stats, get_dataset_file_stats,
    download_from_url, download_from_s3, ensure_storage_dir
)

from tenants.access import get_accessible_tenant_ids


class DatasetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Dataset management.
    
    Provides CRUD operations for datasets including upload, preview, and statistics.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """Return datasets filtered by tenant and user access."""
        user = self.request.user
        queryset = Dataset.objects.filter(
            Q(tenant__isnull=True) | Q(tenant_id__in=get_accessible_tenant_ids(user))
        )

        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source=source)

        data_format = self.request.query_params.get('format')
        if data_format:
            queryset = queryset.filter(format=data_format)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return DatasetListSerializer
        elif self.action == 'create':
            return DatasetCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DatasetUpdateSerializer
        return DatasetSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.delete_file()
        instance.delete()

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def upload(self, request):
        """
        Upload a dataset file.
        
        Accepts multipart/form-data with:
        - file: The dataset file
        - name: Dataset name (optional, defaults to filename)
        - format: Data format override (optional, auto-detected if not provided)
        - description: Dataset description (optional)
        """
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        name = request.data.get('name', file.name)
        description = request.data.get('description', '')
        data_format = request.data.get('format')

        if not data_format:
            data_format = detect_format_from_extension(file.name)

        dataset = Dataset.objects.create(
            name=name,
            description=description,
            source='upload',
            file=file,
            format=data_format,
            status='pending',
            created_by=request.user,
            tenant=self._get_tenant(request)
        )

        try:
            result = self._process_dataset(dataset)
            if result.get('success'):
                dataset.status = 'ready'
                dataset.row_count = result.get('row_count', 0)
                dataset.column_count = result.get('column_count', 0)
                dataset.columns = result.get('columns', [])
                dataset.preview_data = result.get('preview_data', [])
                dataset.size_bytes = result.get('size_bytes', 0)
                dataset.save()
            else:
                dataset.status = 'error'
                dataset.error_message = result.get('error', 'Unknown error')
                dataset.save()
                return Response(
                    {'error': result.get('error', 'Processing failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Failed to process dataset: {str(e)}")
            dataset.status = 'error'
            dataset.error_message = str(e)
            dataset.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DatasetSerializer(dataset)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def create_from_url(self, request):
        """
        Create a dataset from a URL.
        
        Request body:
        - url: The URL to download from
        - name: Dataset name
        - format: Data format (optional, auto-detected from URL)
        - description: Dataset description (optional)
        """
        url = request.data.get('url')
        if not url:
            return Response(
                {'error': 'URL is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        name = request.data.get('name', url.split('/')[-1])
        description = request.data.get('description', '')
        data_format = request.data.get('format', 'csv')

        dataset = Dataset.objects.create(
            name=name,
            description=description,
            source='url',
            url=url,
            format=data_format,
            status='pending',
            created_by=request.user,
            tenant=self._get_tenant(request)
        )

        try:
            ensure_storage_dir()
            file_path, file_size = download_from_url(url)

            dataset.file_path = file_path
            dataset.size_bytes = file_size

            result = self._process_dataset_from_path(dataset, file_path)
            if result.get('success'):
                dataset.status = 'ready'
                dataset.row_count = result.get('row_count', 0)
                dataset.column_count = result.get('column_count', 0)
                dataset.columns = result.get('columns', [])
                dataset.preview_data = result.get('preview_data', [])
                dataset.save()
            else:
                dataset.status = 'error'
                dataset.error_message = result.get('error', 'Unknown error')
                dataset.save()
                return Response(
                    {'error': result.get('error', 'Processing failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Failed to process dataset from URL: {str(e)}")
            dataset.status = 'error'
            dataset.error_message = str(e)
            dataset.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DatasetSerializer(dataset)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def create_from_s3(self, request):
        """
        Create a dataset from an S3 path.
        
        Request body:
        - s3_path: The S3 path (s3://bucket/key or bucket/key)
        - name: Dataset name
        - format: Data format (optional)
        - description: Dataset description (optional)
        """
        s3_path = request.data.get('s3_path')
        if not s3_path:
            return Response(
                {'error': 'S3 path is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        name = request.data.get('name', s3_path.split('/')[-1])
        description = request.data.get('description', '')
        data_format = request.data.get('format', 'csv')

        dataset = Dataset.objects.create(
            name=name,
            description=description,
            source='s3',
            s3_path=s3_path,
            format=data_format,
            status='pending',
            created_by=request.user,
            tenant=self._get_tenant(request)
        )

        try:
            ensure_storage_dir()
            file_path, file_size = download_from_s3(s3_path)

            dataset.file_path = file_path
            dataset.size_bytes = file_size

            result = self._process_dataset_from_path(dataset, file_path)
            if result.get('success'):
                dataset.status = 'ready'
                dataset.row_count = result.get('row_count', 0)
                dataset.column_count = result.get('column_count', 0)
                dataset.columns = result.get('columns', [])
                dataset.preview_data = result.get('preview_data', [])
                dataset.save()
            else:
                dataset.status = 'error'
                dataset.error_message = result.get('error', 'Unknown error')
                dataset.save()
                return Response(
                    {'error': result.get('error', 'Processing failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ImportError as e:
            dataset.status = 'error'
            dataset.error_message = str(e)
            dataset.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Failed to process dataset from S3: {str(e)}")
            dataset.status = 'error'
            dataset.error_message = str(e)
            dataset.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DatasetSerializer(dataset)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """
        Get dataset preview (first 100 rows).
        """
        dataset = self.get_object()

        if not dataset.is_ready:
            return Response(
                {'error': 'Dataset is not ready'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if dataset.preview_data:
            return Response({
                'columns': dataset.columns,
                'rows': dataset.preview_data,
                'row_count': dataset.row_count,
                'total_rows': dataset.row_count,
                'preview_rows': len(dataset.preview_data)
            })

        file_path = dataset.get_absolute_file_path()
        if not file_path or not os.path.exists(file_path):
            return Response(
                {'error': 'Dataset file not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            preview_data = parse_dataset_file(file_path, dataset.format, max_rows=100)
            return Response({
                'columns': preview_data.get('columns', []),
                'rows': preview_data.get('rows', []),
                'row_count': preview_data.get('row_count', 0),
                'total_rows': preview_data.get('total_rows', 0),
                'preview_rows': preview_data.get('preview_rows', 0)
            })
        except Exception as e:
            logger.error(f"Failed to get preview for dataset {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Get dataset statistics.
        """
        dataset = self.get_object()

        if not dataset.is_ready:
            return Response(
                {'error': 'Dataset is not ready'},
                status=status.HTTP_400_BAD_REQUEST
            )

        file_path = dataset.get_absolute_file_path()
        if not file_path or not os.path.exists(file_path):
            return Response(
                {'error': 'Dataset file not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            stats = get_dataset_file_stats(file_path, dataset.format)
            return Response({
                'row_count': stats.get('row_count', dataset.row_count),
                'column_count': stats.get('column_count', dataset.column_count),
                'columns': stats.get('columns', dataset.columns),
                'size_bytes': stats.get('size_bytes', dataset.size_bytes),
                'size_display': stats.get('size_display', ''),
                'format': dataset.format,
                'source': dataset.source,
                'null_counts': stats.get('null_counts', {}),
                'unique_counts': stats.get('unique_counts', {}),
                'numeric_stats': stats.get('numeric_stats', {})
            })
        except Exception as e:
            logger.error(f"Failed to get stats for dataset {pk}: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """
        Reprocess a dataset to update statistics.
        """
        dataset = self.get_object()

        file_path = dataset.get_absolute_file_path()
        if not file_path or not os.path.exists(file_path):
            return Response(
                {'error': 'Dataset file not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        dataset.status = 'pending'
        dataset.save()

        try:
            result = self._process_dataset_from_path(dataset, file_path)
            if result.get('success'):
                dataset.status = 'ready'
                dataset.row_count = result.get('row_count', 0)
                dataset.column_count = result.get('column_count', 0)
                dataset.columns = result.get('columns', [])
                dataset.preview_data = result.get('preview_data', [])
                dataset.size_bytes = result.get('size_bytes', 0)
                dataset.error_message = ''
                dataset.save()
            else:
                dataset.status = 'error'
                dataset.error_message = result.get('error', 'Unknown error')
                dataset.save()
                return Response(
                    {'error': result.get('error', 'Reprocessing failed')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Failed to reprocess dataset {pk}: {str(e)}")
            dataset.status = 'error'
            dataset.error_message = str(e)
            dataset.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DatasetSerializer(dataset)
        return Response(serializer.data)

    def _get_tenant(self, request):
        """Get user's primary active tenant."""
        ids = get_accessible_tenant_ids(request.user)
        if not ids:
            return None
        from tenants.models import Tenant
        return Tenant.objects.filter(id=ids[0]).first()

    def _process_dataset(self, dataset):
        """Process an uploaded dataset file."""
        if not dataset.file:
            return {'success': False, 'error': 'No file associated with dataset'}

        file_path = dataset.file.path

        if not os.path.exists(file_path):
            return {'success': False, 'error': 'File not found'}

        return self._process_dataset_from_path(dataset, file_path)

    def _process_dataset_from_path(self, dataset, file_path):
        """Process a dataset from a file path."""
        try:
            file_size = os.path.getsize(file_path)
            preview_data = parse_dataset_file(file_path, dataset.format, max_rows=100)

            return {
                'success': True,
                'row_count': preview_data.get('row_count', 0),
                'column_count': len(preview_data.get('columns', [])),
                'columns': preview_data.get('columns', []),
                'preview_data': preview_data.get('rows', []),
                'size_bytes': file_size
            }
        except Exception as e:
            logger.error(f"Failed to process dataset from path {file_path}: {str(e)}")
            return {'success': False, 'error': str(e)}
