"""
Marketplace API for workflow templates.
"""

import uuid
from django.db.models import Prefetch
from django.db.models import Prefetch
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import WorkflowTemplate, TemplateCategory, TemplateInstall, TemplateRating
from .serializers import (
    WorkflowTemplateSerializer,
    TemplateCategorySerializer,
    TemplateInstallSerializer,
    TemplateRatingSerializer,
    TemplateCreateSerializer
)


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow templates (marketplace)."""

    permission_classes = [AllowAny]  # Marketplace is public

    def get_queryset(self):
        queryset = WorkflowTemplate.objects.filter(is_published=True)

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        # Filter by tags
        tags = self.request.query_params.get('tags')
        if tags:
            tag_list = tags.split(',')
            queryset = queryset.filter(tags__overlap=tag_list)

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search) | \
                      queryset.filter(description__icontains=search)

        # Sorting
        sort = self.request.query_params.get('sort', 'popular')
        if sort == 'popular':
            queryset = queryset.order_by('-install_count')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'rating':
            queryset = queryset.order_by('-avg_rating')
        elif sort == 'name':
            queryset = queryset.order_by('name')

        return queryset.select_related('category', 'created_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return TemplateCreateSerializer
        if self.action == 'list':
            return WorkflowTemplateSerializer
        return WorkflowTemplateSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured templates."""
        queryset = self.get_queryset().filter(is_featured=True)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get published templates grouped by category."""
        template_queryset = WorkflowTemplate.objects.filter(
            is_published=True
        ).select_related('category', 'created_by').order_by('-install_count', '-created_at')

        categories = TemplateCategory.objects.prefetch_related(
            Prefetch('templates', queryset=template_queryset, to_attr='published_templates')
        )

        result = []
        for category in categories:
            templates = getattr(category, 'published_templates', [])
            if not templates:
                continue

            serializer = self.get_serializer(templates[:4], many=True)
            result.append({
                'category': TemplateCategorySerializer(category, context={'request': request}).data,
                'templates': serializer.data,
            })

        return Response(result)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def install(self, request, pk=None):
        """Install a template."""
        template = self.get_object()

        # Check if already installed
        if TemplateInstall.objects.filter(
            user=request.user,
            template=template
        ).exists():
            return Response(
                {'error': 'Template already installed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create install record
        install = TemplateInstall.objects.create(
            user=request.user,
            template=template
        )

        return Response({
            'message': 'Template installed successfully',
            'install': TemplateInstallSerializer(install).data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        """Rate a template."""
        template = self.get_object()
        rating_value = request.data.get('rating')

        if not rating_value or not (1 <= rating_value <= 5):
            return Response(
                {'error': 'Rating must be between 1 and 5'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create or update rating
        rating, created = TemplateRating.objects.update_or_create(
            user=request.user,
            template=template,
            defaults={'rating': rating_value}
        )

        # Recalculate average rating
        avg_rating = TemplateRating.objects.filter(
            template=template
        ).aggregate(Avg('rating'))['rating__avg']

        template.avg_rating = avg_rating or 0
        template.save(update_fields=['avg_rating', 'updated_at'])

        return Response({
            'user_rating': rating.rating,
            'rating': float(avg_rating or 0),
            'avg_rating': float(avg_rating or 0),
            'rating_count': template.ratings.count()
        })

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get template statistics."""
        template = self.get_object()

        return Response({
            'use_count': template.install_count,
            'installs': template.install_count,
            'rating': template.avg_rating,
            'avg_rating': template.avg_rating,
            'rating_count': template.ratings.count(),
            'views': template.view_count
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def report(self, request, pk=None):
        """Report a template as inappropriate."""
        template = self.get_object()
        reason = request.data.get('reason', '')

        # Create report (could add a Report model)
        template.report_count += 1
        template.save()

        return Response({'message': 'Report submitted'})


class TemplateCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for template categories."""

    queryset = TemplateCategory.objects.all()
    serializer_class = TemplateCategorySerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['get'])
    def templates(self, request, pk=None):
        """Get templates in this category."""
        category = self.get_object()
        templates = WorkflowTemplate.objects.filter(
            category=category,
            is_published=True
        ).order_by('-install_count')

        page = self.paginate_queryset(templates)
        if page is not None:
            serializer = WorkflowTemplateSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = WorkflowTemplateSerializer(templates, many=True)
        return Response(serializer.data)


class MyTemplatesViewSet(viewsets.ModelViewSet):
    """ViewSet for user's own templates."""

    serializer_class = WorkflowTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkflowTemplate.objects.filter(
            created_by=self.request.user
        ).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a template."""
        template = self.get_object()
        template.is_published = True
        template.save(update_fields=['is_published', 'updated_at'])
        serializer = WorkflowTemplateSerializer(template, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish a template."""
        template = self.get_object()
        template.is_published = False
        template.save(update_fields=['is_published', 'updated_at'])
        serializer = WorkflowTemplateSerializer(template, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def installs(self, request, pk=None):
        """Get install history for this template."""
        template = self.get_object()
        installs = TemplateInstall.objects.filter(
            template=template
        ).select_related('user').order_by('-installed_at')

        page = self.paginate_queryset(installs)
        if page is not None:
            serializer = TemplateInstallSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TemplateInstallSerializer(installs, many=True)
        return Response(serializer.data)


class InstalledTemplatesViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for user's installed templates."""

    serializer_class = WorkflowTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        install_ids = TemplateInstall.objects.filter(
            user=self.request.user
        ).values_list('template_id', flat=True)

        return WorkflowTemplate.objects.filter(
            id__in=install_ids
        ).order_by('-created_at')
