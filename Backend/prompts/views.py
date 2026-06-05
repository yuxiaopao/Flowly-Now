"""
Prompt template API views.
"""

from django.db.models import Q, Avg
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import PromptTemplate, PromptCategory, PromptVersion, PromptUsage, PromptRating
from .serializers import (
    PromptTemplateListSerializer, PromptTemplateDetailSerializer,
    PromptTemplateCreateSerializer, PromptCategorySerializer,
    PromptVersionSerializer, PromptUsageSerializer, PromptRatingSerializer
)


class PromptCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for prompt categories."""

    queryset = PromptCategory.objects.filter(is_active=True)
    serializer_class = PromptCategorySerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get category tree structure."""
        root_categories = self.queryset.filter(parent__isnull=True)
        data = []

        for category in root_categories:
            data.append(self._build_tree(category))

        return Response(data)

    def _build_tree(self, category):
        """Build tree structure for a category."""
        children = PromptCategory.objects.filter(parent=category, is_active=True)
        return {
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'icon': category.icon,
            'color': category.color,
            'children': [self._build_tree(c) for c in children]
        }


class PromptTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for prompt templates."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = PromptTemplate.objects.filter(
            Q(is_public=True) | Q(created_by=self.request.user)
        )

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)

        # Filter by type
        prompt_type = self.request.query_params.get('type')
        if prompt_type:
            queryset = queryset.filter(prompt_type=prompt_type)

        # Filter by tags
        tag = self.request.query_params.get('tag')
        if tag:
            queryset = queryset.filter(tags__contains=[tag])

        # Filter by search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        # Filter by featured
        featured = self.request.query_params.get('featured')
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)

        # Sorting
        sort = self.request.query_params.get('sort', '-use_count')
        if sort == 'rating':
            queryset = queryset.order_by('-avg_rating', '-rating_count')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-use_count')

        return queryset.select_related('category', 'created_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return PromptTemplateListSerializer
        return PromptTemplateDetailSerializer

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured prompts."""
        prompts = self.get_queryset().filter(
            is_featured=True
        ).order_by('-use_count')[:10]

        return Response(PromptTemplateListSerializer(
            prompts, many=True, context={'request': request}
        ).data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently used prompts."""
        prompts = self.get_queryset().order_by('-created_at')[:10]
        return Response(PromptTemplateListSerializer(
            prompts, many=True, context={'request': request}
        ).data)

    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """Render prompt with variables."""
        prompt = self.get_object()
        variables = request.data.get('variables', {})

        rendered = self._render_template(prompt.template, variables)

        return Response({
            'rendered': rendered,
            'variables': variables
        })

    def _render_template(self, template, variables):
        """Render prompt template with variables."""
        result = template
        for key, value in variables.items():
            placeholder = '{' + key + '}'
            result = result.replace(placeholder, str(value))
        return result

    @action(detail=True, methods=['post'])
    def use(self, request, pk=None):
        """Track prompt usage."""
        prompt = self.get_object()

        usage = PromptUsage.objects.create(
            prompt=prompt,
            user=request.user,
            workflow_id=request.data.get('workflow_id'),
            node_id=request.data.get('node_id', ''),
            input_variables=request.data.get('variables', {}),
            rendered_prompt=request.data.get('rendered_prompt', ''),
            was_successful=request.data.get('was_successful', True)
        )

        prompt.increment_use()

        return Response(PromptUsageSerializer(usage).data)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Rate a prompt."""
        prompt = self.get_object()

        rating_value = request.data.get('rating')
        if not rating_value or not (1 <= rating_value <= 5):
            return Response(
                {'error': 'Rating must be between 1 and 5'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rating, created = PromptRating.objects.update_or_create(
            prompt=prompt,
            user=request.user,
            defaults={
                'rating': rating_value,
                'comment': request.data.get('comment', '')
            }
        )

        # Update prompt average rating
        ratings = PromptRating.objects.filter(prompt=prompt)
        avg_rating = ratings.aggregate(Avg('rating'))['rating__avg'] or 0
        prompt.avg_rating = avg_rating
        prompt.rating_count = ratings.count()
        prompt.save(update_fields=['avg_rating', 'rating_count'])

        return Response({
            'rating': PromptRatingSerializer(rating).data,
            'avg_rating': avg_rating
        })

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get prompt version history."""
        prompt = self.get_object()
        versions = prompt.versions.all()
        return Response(PromptVersionSerializer(versions, many=True).data)

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """Create a new version of a prompt."""
        prompt = self.get_object()

        if prompt.created_by != request.user:
            return Response(
                {'error': 'Only the creator can create versions'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get next version number
        last_version = prompt.versions.order_by('-version').first()
        if last_version:
            try:
                major, minor = last_version.version.split('.')
                new_version = f"{major}.{int(minor) + 1}"
            except Exception:
                new_version = "1.1"
        else:
            new_version = "1.1"

        version = PromptVersion.objects.create(
            prompt=prompt,
            version=new_version,
            template=request.data.get('template', prompt.template),
            variables=request.data.get('variables', prompt.variables),
            changelog=request.data.get('changelog', ''),
            created_by=request.user
        )

        # Update prompt with new template
        prompt.template = version.template
        prompt.variables = version.variables
        prompt.version = new_version
        prompt.save()

        return Response(PromptVersionSerializer(version).data, status=status.HTTP_201_CREATED)


class MyPromptViewSet(viewsets.ModelViewSet):
    """ViewSet for user's own prompts."""

    serializer_class = PromptTemplateDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PromptTemplate.objects.filter(
            created_by=self.request.user
        ).select_related('category', 'created_by')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user's prompt statistics."""
        from django.db.models import Sum
        prompts = self.get_queryset()
        total_uses = prompts.aggregate(total=Sum('use_count'))['total'] or 0
        total_ratings = prompts.aggregate(total=Sum('rating_count'))['total'] or 0

        return Response({
            'total_prompts': prompts.count(),
            'total_uses': total_uses,
            'total_ratings': total_ratings,
            'public_prompts': prompts.filter(is_public=True).count(),
            'featured_prompts': prompts.filter(is_featured=True).count()
        })

    @action(detail=False, methods=['get'])
    def usage_history(self, request):
        """Get prompt usage history."""
        usages = PromptUsage.objects.filter(
            prompt__created_by=request.user
        ).select_related('prompt', 'workflow').order_by('-created_at')[:50]

        return Response(PromptUsageSerializer(usages, many=True).data)
