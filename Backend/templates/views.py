"""
Workflow template API views.
"""

from collections import defaultdict
from django.db.models import Q, Avg, Count, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import (
    TemplateCategory, WorkflowTemplate, TemplateVersion,
    TemplateUsage, TemplateReview, TemplateFavorite
)
from .serializers import (
    TemplateCategorySerializer, WorkflowTemplateListSerializer,
    WorkflowTemplateDetailSerializer, WorkflowTemplateCreateSerializer,
    TemplateVersionSerializer, TemplateReviewSerializer, TemplateUsageSerializer
)


class TemplateCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for template categories."""

    queryset = TemplateCategory.objects.filter(is_active=True)
    serializer_class = TemplateCategorySerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get category tree structure."""
        all_active = list(TemplateCategory.objects.filter(is_active=True))
        children_map = defaultdict(list)
        for cat in all_active:
            children_map[cat.parent_id].append(cat)

        data = [self._build_tree(cat, children_map) for cat in children_map[None]]
        return Response(data)

    def _build_tree(self, category, children_map):
        """Build tree structure for a category."""
        return {
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'icon': category.icon,
            'color': category.color,
            'children': [self._build_tree(c, children_map) for c in children_map[category.id]]
        }


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for workflow templates."""

    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = WorkflowTemplate.objects.filter(status='published')

        if self.request.user.is_authenticated:
            queryset = WorkflowTemplate.objects.filter(
                Q(status='published') | Q(created_by=self.request.user)
            )

        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        access = self.request.query_params.get('access')
        if access:
            queryset = queryset.filter(access=access)

        verified = self.request.query_params.get('verified')
        if verified == 'true':
            queryset = queryset.filter(is_verified=True)

        sort = self.request.query_params.get('sort', '-use_count')
        if sort == 'rating':
            queryset = queryset.order_by('-rating', '-rating_count')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort == 'oldest':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-use_count')

        return queryset.select_related('category', 'created_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowTemplateListSerializer
        return WorkflowTemplateDetailSerializer

    def _serialize_templates(self, templates, request):
        return WorkflowTemplateListSerializer(templates, many=True, context={'request': request}).data

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured templates."""
        templates = self.get_queryset().filter(
            is_verified=True
        ).order_by('-use_count', '-rating')[:8]
        return Response(self._serialize_templates(templates, request))

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular templates."""
        templates = self.get_queryset().order_by('-use_count')[:12]
        return Response(self._serialize_templates(templates, request))

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently published templates."""
        templates = self.get_queryset().order_by('-published_at', '-created_at')[:12]
        return Response(self._serialize_templates(templates, request))

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Get template preview (without full workflow data)."""
        template = self.get_object()
        WorkflowTemplate.objects.filter(pk=template.pk).update(view_count=F('view_count') + 1)
        template.refresh_from_db(fields=['view_count'])

        data = WorkflowTemplateListSerializer(template, context={'request': request}).data
        data['nodes'] = template.nodes
        data['edges'] = template.edges

        return Response(data)

    @action(detail=True, methods=['post'])
    def use(self, request, pk=None):
        """Use template to create workflow."""
        template = self.get_object()

        if template.access == 'private' and template.created_by != request.user:
            return Response(
                {'error': 'This template is private'},
                status=status.HTTP_403_FORBIDDEN
            )

        from workflows.models import Workflow
        workflow = Workflow.objects.create(
            name=f"{template.name} (from template)",
            description=template.description,
            nodes=template.nodes,
            edges=template.edges,
            variables=template.variables,
            owner=request.user
        )

        TemplateUsage.objects.create(
            template=template,
            user=request.user,
            workflow=workflow
        )
        WorkflowTemplate.objects.filter(pk=template.pk).update(use_count=F('use_count') + 1)

        return Response({
            'workflow_id': workflow.id,
            'workflow_name': workflow.name
        })

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Like/unlike template."""
        template = self.get_object()

        if template.likes.filter(id=request.user.id).exists():
            template.likes.remove(request.user)
            WorkflowTemplate.objects.filter(pk=template.pk).update(like_count=F('like_count') - 1)
            liked = False
        else:
            template.likes.add(request.user)
            WorkflowTemplate.objects.filter(pk=template.pk).update(like_count=F('like_count') + 1)
            liked = True

        template.refresh_from_db(fields=['like_count'])
        return Response({'liked': liked, 'like_count': template.like_count})

    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        """Add/remove template from favorites."""
        template = self.get_object()

        favorite, created = TemplateFavorite.objects.get_or_create(
            template=template,
            user=request.user
        )

        if not created:
            favorite.delete()
            favorited = False
        else:
            favorited = True

        return Response({'favorited': favorited})

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get template reviews."""
        template = self.get_object()
        reviews = template.reviews.all()

        sort = request.query_params.get('sort', '-helpful_count')
        if sort == 'newest':
            reviews = reviews.order_by('-created_at')
        elif sort == 'oldest':
            reviews = reviews.order_by('created_at')
        elif sort == 'rating_high':
            reviews = reviews.order_by('-rating')
        elif sort == 'rating_low':
            reviews = reviews.order_by('rating')
        else:
            reviews = reviews.order_by('-helpful_count')

        return Response(TemplateReviewSerializer(reviews, many=True).data)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Add review to template."""
        template = self.get_object()

        if TemplateReview.objects.filter(template=template, user=request.user).exists():
            return Response(
                {'error': 'You have already reviewed this template'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TemplateReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(template=template, user=request.user)

        stats = template.reviews.aggregate(avg=Avg('rating'), count=Count('id'))
        template.rating = stats['avg'] or 0
        template.rating_count = stats['count']
        template.save(update_fields=['rating', 'rating_count'])

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for user's own templates."""

    serializer_class = WorkflowTemplateDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkflowTemplate.objects.filter(
            created_by=self.request.user
        ).select_related('category', 'created_by')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def favorites(self, request):
        """Get user's favorite templates."""
        templates = WorkflowTemplate.objects.filter(
            favorites__user=request.user
        ).select_related('category', 'created_by')

        return Response(WorkflowTemplateListSerializer(templates, many=True, context={'request': request}).data)

    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get user's reviews."""
        reviews = TemplateReview.objects.filter(
            user=request.user
        ).select_related('template')

        return Response(TemplateReviewSerializer(reviews, many=True).data)


class TemplateVersionViewSet(viewsets.ModelViewSet):
    """ViewSet for template versions."""

    serializer_class = TemplateVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        template_id = self.request.query_params.get('template_id')
        if template_id:
            return TemplateVersion.objects.filter(
                template_id=template_id,
                template__created_by=self.request.user
            )
        return TemplateVersion.objects.none()

    def perform_create(self, serializer):
        template_id = self.request.data.get('template_id')
        template = WorkflowTemplate.objects.get(id=template_id)

        serializer.save(
            template=template,
            created_by=self.request.user
        )
