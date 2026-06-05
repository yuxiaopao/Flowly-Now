"""
Marketplace serializers for workflow templates.
"""

from rest_framework import serializers
from .models import (
    WorkflowTemplate, TemplateCategory, TemplateInstall,
    TemplateRating, TemplateComment, TemplateFavorite
)


class TemplateCategorySerializer(serializers.ModelSerializer):
    """Serializer for template categories."""

    template_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'order', 'template_count']

    def get_template_count(self, obj):
        return obj.templates.filter(is_published=True).count()


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Serializer for workflow templates."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    author_name = serializers.CharField(source='created_by.username', read_only=True)
    author_avatar = serializers.SerializerMethodField()
    is_installed = serializers.SerializerMethodField()
    use_count = serializers.IntegerField(source='install_count', read_only=True)
    rating = serializers.FloatField(source='avg_rating', read_only=True)
    thumbnail = serializers.CharField(source='preview_image', read_only=True)
    is_public = serializers.BooleanField(source='is_published', read_only=True)
    node_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'category_name',
            'category_slug', 'tags', 'workflow_data', 'nodes', 'edges', 'node_count',
            'use_count', 'view_count', 'rating', 'report_count', 'rating_count',
            'thumbnail', 'is_public', 'is_featured', 'is_verified',
            'created_by', 'author_name', 'author_avatar', 'is_installed',
            'created_at', 'updated_at'
        ]

    def get_author_avatar(self, obj):
        if hasattr(obj.created_by, 'profile') and obj.created_by.profile.avatar:
            return obj.created_by.profile.avatar.url
        return None

    def get_is_installed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.installs.filter(user=request.user).exists()
        return False

    def get_node_count(self, obj):
        if isinstance(obj.nodes, list):
            return len(obj.nodes)
        workflow_data = obj.workflow_data or {}
        nodes = workflow_data.get('nodes') if isinstance(workflow_data, dict) else None
        return len(nodes) if isinstance(nodes, list) else 0


class TemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating workflow templates."""

    thumbnail = serializers.CharField(source='preview_image', required=False, allow_blank=True)
    is_public = serializers.BooleanField(source='is_published', required=False)

    class Meta:
        model = WorkflowTemplate
        fields = [
            'name', 'slug', 'description', 'category', 'tags',
            'workflow_data', 'nodes', 'edges', 'thumbnail', 'is_public'
        ]

    def validate_slug(self, value):
        """Validate slug is unique."""
        if WorkflowTemplate.objects.filter(slug=value).exists():
            raise serializers.ValidationError("A template with this slug already exists.")
        return value


class TemplateInstallSerializer(serializers.ModelSerializer):
    """Serializer for template installs."""

    template_name = serializers.CharField(source='template.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TemplateInstall
        fields = ['id', 'user', 'username', 'template', 'template_name', 'workflow', 'installed_at']


class TemplateRatingSerializer(serializers.ModelSerializer):
    """Serializer for template ratings."""

    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TemplateRating
        fields = ['id', 'user', 'username', 'template', 'rating', 'created_at']


class TemplateCommentSerializer(serializers.ModelSerializer):
    """Serializer for template comments."""

    username = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateComment
        fields = [
            'id', 'template', 'user', 'username', 'user_avatar', 'content',
            'parent', 'like_count', 'replies', 'reply_count', 'created_at'
        ]

    def get_user_avatar(self, obj):
        if hasattr(obj.user, 'profile') and obj.user.profile.avatar:
            return obj.user.profile.avatar.url
        return None

    def get_replies(self, obj):
        if obj.parent is None:
            replies = obj.replies.all()[:5]
            return TemplateCommentSerializer(replies, many=True, context=self.context).data
        return []

    def get_reply_count(self, obj):
        return obj.replies.count()


class TemplateFavoriteSerializer(serializers.ModelSerializer):
    """Serializer for template favorites."""

    template_name = serializers.CharField(source='template.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TemplateFavorite
        fields = ['id', 'user', 'username', 'template', 'template_name', 'created_at']
