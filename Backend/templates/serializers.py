"""
Workflow template serializers.
"""

from rest_framework import serializers
from .models import (
    TemplateCategory, WorkflowTemplate, TemplateVersion,
    TemplateUsage, TemplateReview, TemplateFavorite
)


class TemplateCategorySerializer(serializers.ModelSerializer):
    """Serializer for template categories."""

    template_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'color',
            'parent', 'sort_order', 'is_active', 'template_count',
            'created_at', 'updated_at'
        ]

    def get_template_count(self, obj):
        return obj.templates.filter(status='published').count()


class TemplateVersionSerializer(serializers.ModelSerializer):
    """Serializer for template versions."""

    class Meta:
        model = TemplateVersion
        fields = [
            'id', 'version', 'name', 'nodes', 'edges', 'variables',
            'changelog', 'created_by', 'created_at'
        ]


class TemplateReviewSerializer(serializers.ModelSerializer):
    """Serializer for template reviews."""

    user_name = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = TemplateReview
        fields = [
            'id', 'user', 'user_name', 'user_avatar', 'rating',
            'title', 'content', 'is_verified', 'helpful_count',
            'created_at', 'updated_at'
        ]

    def get_user_avatar(self, obj):
        if hasattr(obj.user, 'profile') and obj.user.profile.avatar:
            return obj.user.profile.avatar.url
        return None


class WorkflowTemplateListSerializer(serializers.ModelSerializer):
    """Serializer for template list view."""

    category_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'tags', 'thumbnail', 'view_count', 'use_count', 'like_count',
            'rating', 'rating_count', 'is_verified', 'creator_name',
            'is_favorited', 'created_at'
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ''

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ''

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and hasattr(obj, 'likes'):
            return obj.likes.filter(id=request.user.id).exists()
        return False


class WorkflowTemplateDetailSerializer(serializers.ModelSerializer):
    """Serializer for template detail view."""

    category = TemplateCategorySerializer(read_only=True)
    creator_name = serializers.SerializerMethodField()

    def get_creator_name(self, obj):
        return obj.created_by.username if obj.created_by else ''
    creator_avatar = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_used = serializers.SerializerMethodField()
    versions = TemplateVersionSerializer(many=True, read_only=True)
    reviews = TemplateReviewSerializer(many=True, read_only=True)
    review_count = serializers.IntegerField(source='reviews.count', read_only=True)

    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'name', 'description', 'category', 'tags',
            'nodes', 'edges', 'variables', 'thumbnail', 'preview_images',
            'view_count', 'use_count', 'like_count', 'rating', 'rating_count',
            'is_verified', 'verified_at', 'status', 'access',
            'created_by', 'creator_name', 'creator_avatar',
            'is_favorited', 'is_used', 'versions', 'reviews', 'review_count',
            'published_at', 'created_at', 'updated_at'
        ]

    def get_creator_avatar(self, obj):
        if hasattr(obj.created_by, 'profile') and obj.created_by.profile.avatar:
            return obj.created_by.profile.avatar.url
        return None

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and hasattr(obj, 'likes'):
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_is_used(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and hasattr(obj, 'usages'):
            return obj.usages.filter(user=request.user).exists()
        return False


class WorkflowTemplateCreateSerializer(serializers.Serializer):
    """Serializer for creating templates from workflows."""

    workflow_id = serializers.IntegerField()
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.IntegerField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    is_public = serializers.BooleanField(default=False)
    config = serializers.JSONField(required=False, default=dict)


class TemplateUsageSerializer(serializers.ModelSerializer):
    """Serializer for template usage."""

    user_name = serializers.CharField(source='user.username', read_only=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = TemplateUsage
        fields = [
            'id', 'template', 'user', 'user_name', 'workflow', 'workflow_name',
            'created_at'
        ]


class TemplateFavoriteSerializer(serializers.ModelSerializer):
    """Serializer for template favorites."""

    template_name = serializers.CharField(source='template.name', read_only=True)
    template_thumbnail = serializers.URLField(source='template.thumbnail', read_only=True)

    class Meta:
        model = TemplateFavorite
        fields = [
            'id', 'template', 'template_name', 'template_thumbnail', 'created_at'
        ]
