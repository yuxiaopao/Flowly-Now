"""
Views for annotations app.
"""

import json
import logging
from io import BytesIO
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import AnnotationProject, AnnotationItem
from .serializers import (
    AnnotationProjectSerializer, AnnotationProjectListSerializer,
    AnnotationProjectCreateSerializer, AnnotationProjectUpdateSerializer,
    AnnotationItemSerializer, AnnotationItemUpdateSerializer
)
from .utils import (
    initialize_items_from_dataset, generate_pre_labels, export_annotations,
    export_image_text_pairs,
)

from tenants.access import get_accessible_tenant_ids


class AnnotationProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AnnotationProject management.
    
    Provides CRUD operations for annotation projects.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return projects filtered by tenant and user access."""
        user = self.request.user
        queryset = AnnotationProject.objects.filter(
            Q(tenant__isnull=True) | Q(tenant_id__in=get_accessible_tenant_ids(user))
        )

        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        annotation_type = self.request.query_params.get('annotation_type')
        if annotation_type:
            queryset = queryset.filter(annotation_type=annotation_type)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(dataset__name__icontains=search)
            )

        dataset_id = self.request.query_params.get('dataset')
        if dataset_id:
            queryset = queryset.filter(dataset_id=dataset_id)

        return queryset.select_related('dataset', 'created_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return AnnotationProjectListSerializer
        elif self.action == 'create':
            return AnnotationProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AnnotationProjectUpdateSerializer
        return AnnotationProjectSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        instance.items.all().delete()
        instance.delete()

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """
        Get items for annotation (paginated, 20 items per page).
        """
        project = self.get_object()

        status_filter = request.query_params.get('status')
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        queryset = AnnotationItem.objects.filter(project=project)

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size

        items = queryset[start:end]

        serializer = AnnotationItemSerializer(items, many=True)

        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

        return Response({
            'count': total_count,
            'next': f'?page={page + 1}' if page < total_pages else None,
            'previous': f'?page={page - 1}' if page > 1 else None,
            'results': serializer.data,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        })

    @action(detail=True, methods=['post'])
    def pre_label(self, request, pk=None):
        """
        Generate AI pre-labels for pending items.
        """
        project = self.get_object()

        if not project.model_assisted:
            return Response(
                {'error': 'Model assisted annotation is not enabled for this project'},
                status=status.HTTP_400_BAD_REQUEST
            )

        model_id = request.data.get('model_id')

        try:
            result = generate_pre_labels(project, model_id)

            if result.get('success'):
                return Response({
                    'message': 'Pre-labeling completed',
                    'processed': result.get('processed', 0),
                    'errors': result.get('errors', 0)
                })
            else:
                return Response(
                    {'error': result.get('error', 'Pre-labeling failed')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Pre-labeling error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """
        Export annotations as JSON or CSV.
        """
        project = self.get_object()
        export_format = request.query_params.get('format', 'json')

        try:
            if export_format == 'image_text_pairs':
                result = export_image_text_pairs(project)
                if not result.get('success'):
                    return Response({'error': result.get('error')}, status=status.HTTP_400_BAD_REQUEST)
                response = HttpResponse(
                    result['content'],
                    content_type='application/x-ndjson; charset=utf-8',
                )
                response['Content-Disposition'] = f'attachment; filename="pairs_{project.id}.jsonl"'
                return response

            result = export_annotations(project, export_format)

            if not result.get('success'):
                return Response(
                    {'error': result.get('error', 'Export failed')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            if export_format == 'csv':
                response = HttpResponse(
                    result['content'],
                    content_type='text/csv; charset=utf-8'
                )
                response['Content-Disposition'] = f'attachment; filename="annotations_{project.id}.csv"'
                return response
            else:
                response = HttpResponse(
                    json.dumps(result['data'], ensure_ascii=False, indent=2),
                    content_type='application/json; charset=utf-8'
                )
                response['Content-Disposition'] = f'attachment; filename="annotations_{project.id}.json"'
                return response

        except Exception as e:
            logger.error(f"Export error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start annotation - initialize items from dataset.
        """
        project = self.get_object()

        if project.status not in ['draft', 'in_progress']:
            return Response(
                {'error': 'Project cannot be started in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = initialize_items_from_dataset(project)

            if result.get('success'):
                project.refresh_from_db()
                serializer = AnnotationProjectSerializer(project)
                return Response({
                    'message': 'Annotation started successfully',
                    'item_count': result.get('item_count', 0),
                    'project': serializer.data
                })
            else:
                return Response(
                    {'error': result.get('error', 'Failed to start annotation')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Start annotation error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Mark project as complete and export labeled dataset.
        """
        project = self.get_object()

        if project.status == 'completed':
            return Response(
                {'error': 'Project is already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            project.status = 'completed'
            project.save()

            export_result = export_annotations(project, 'json')

            serializer = AnnotationProjectSerializer(project)

            return Response({
                'message': 'Annotation completed successfully',
                'project': serializer.data,
                'export': {
                    'format': 'json',
                    'count': export_result.get('count', 0)
                } if export_result.get('success') else None
            })

        except Exception as e:
            logger.error(f"Complete annotation error: {str(e)}")
            project.status = 'in_progress'
            project.save()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get overall annotation statistics.
        """
        user = request.user

        tenant_ids = get_accessible_tenant_ids(user)

        total_projects = AnnotationProject.objects.filter(
            Q(tenant__isnull=True) | Q(tenant_id__in=tenant_ids)
        ).count()

        completed_projects = AnnotationProject.objects.filter(
            Q(tenant__isnull=True) | Q(tenant_id__in=tenant_ids),
            status='completed'
        ).count()

        total_items = AnnotationItem.objects.filter(
            project__in=AnnotationProject.objects.filter(
                Q(tenant__isnull=True) | Q(tenant_id__in=tenant_ids)
            )
        ).count()

        annotated_items = AnnotationItem.objects.filter(
            project__in=AnnotationProject.objects.filter(
                Q(tenant__isnull=True) | Q(tenant_id__in=tenant_ids)
            ),
            status='annotated'
        ).count()

        return Response({
            'total_projects': total_projects,
            'completed_projects': completed_projects,
            'total_items': total_items,
            'annotated_items': annotated_items,
            'progress_percentage': round((annotated_items / total_items * 100), 1) if total_items > 0 else 0
        })


class AnnotationItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AnnotationItem management.
    
    Provides update operations for individual annotation items.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        """Return items filtered by accessible project."""
        user = self.request.user
        tenant_ids = get_accessible_tenant_ids(user)
        project_id = self.request.query_params.get('project')

        accessible_projects = AnnotationProject.objects.filter(
            Q(created_by=user) | Q(tenant_id__in=tenant_ids)
        )
        if project_id:
            accessible_projects = accessible_projects.filter(id=project_id)

        queryset = AnnotationItem.objects.filter(
            project__in=accessible_projects.values_list('id', flat=True)
        )
        return queryset.select_related('project', 'annotated_by')

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return AnnotationItemUpdateSerializer
        return AnnotationItemSerializer

    def partial_update(self, request, *args, **kwargs):
        """
        Update item label (annotate).
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        if 'status' in data and data['status'] == 'annotated':
            instance.annotated_by = request.user
            instance.annotated_at = __import__('django.utils.timezone').now()

            project = instance.project
            if instance.status != 'annotated':
                project.annotated_items = project.items.filter(status='annotated').count() + 1
                project.save()

        self.perform_update(serializer)

        output_serializer = AnnotationItemSerializer(instance)
        return Response(output_serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """
        Bulk update multiple items with the same label.
        """
        item_ids = request.data.get('item_ids', [])
        label = request.data.get('label')
        item_status = request.data.get('status', 'annotated')

        if not item_ids:
            return Response(
                {'error': 'item_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        items = AnnotationItem.objects.filter(id__in=item_ids)

        if item_status == 'annotated' and not label:
            return Response(
                {'error': 'label is required for annotated status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone
        now = timezone.now()

        updated_count = items.update(
            label=label or '',
            status=item_status,
            annotated_by=request.user if item_status == 'annotated' else None,
            annotated_at=now if item_status == 'annotated' else None
        )

        project_ids = items.values_list('project_id', flat=True).distinct()
        for project_id in project_ids:
            project = AnnotationProject.objects.get(id=project_id)
            project.annotated_items = project.items.filter(status='annotated').count()
            project.save()

        return Response({
            'message': f'Updated {updated_count} items',
            'updated_count': updated_count
        })
