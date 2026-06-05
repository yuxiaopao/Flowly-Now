"""
Prompt template serializers.
"""

from rest_framework import serializers
from .models import PromptTemplate, PromptCategory, PromptVersion, PromptUsage, PromptRating


class PromptCategorySerializer(serializers.ModelSerializer):
    """Serializer for prompt categories."""

    prompt_count = serializers.SerializerMethodField()

    class Meta:
        model = PromptCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'color',
            'parent', 'sort_order', 'is_active', 'prompt_count', 'created_at'
        ]

    def get_prompt_count(self, obj):
        return obj.prompts.filter(is_active=True).count()


class PromptTemplateListSerializer(serializers.ModelSerializer):
    """Serializer for prompt template list."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PromptTemplate
        fields = [
            'id', 'name', 'description', 'prompt_type', 'category',
            'category_name', 'tags', 'use_count', 'avg_rating',
            'rating_count', 'is_featured', 'creator_name', 'created_at'
        ]


class PromptTemplateDetailSerializer(serializers.ModelSerializer):
    """Serializer for prompt template detail."""

    category = PromptCategorySerializer(read_only=True)
    creator_name = serializers.CharField(source='created_by.username', read_only=True)
    is_used = serializers.SerializerMethodField()

    class Meta:
        model = PromptTemplate
        fields = [
            'id', 'name', 'description', 'prompt_type', 'template',
            'variables', 'example_variables', 'model_preferences',
            'temperature', 'max_tokens', 'category', 'tags',
            'use_count', 'success_rate', 'avg_rating', 'rating_count',
            'is_public', 'is_featured', 'version',
            'created_by', 'creator_name', 'is_used',
            'created_at', 'updated_at'
        ]

    def get_is_used(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.usages.filter(user=request.user).exists()
        return False


class PromptTemplateCreateSerializer(serializers.Serializer):
    """Serializer for creating prompts."""

    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    prompt_type = serializers.ChoiceField(choices=['system', 'user', 'assistant', 'task'])
    template = serializers.CharField()
    variables = serializers.ListField(required=False, default=list)
    example_variables = serializers.DictField(required=False, default=dict)
    category_id = serializers.IntegerField(required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class PromptUsageSerializer(serializers.ModelSerializer):
    """Serializer for prompt usage."""

    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = PromptUsage
        fields = [
            'id', 'prompt', 'workflow', 'workflow_name', 'node_id',
            'input_variables', 'rendered_prompt', 'was_successful',
            'feedback', 'created_at'
        ]


class PromptVersionSerializer(serializers.ModelSerializer):
    """Serializer for prompt versions."""

    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PromptVersion
        fields = [
            'id', 'version', 'template', 'variables', 'changelog',
            'created_by', 'created_by_name', 'created_at'
        ]


class PromptRatingSerializer(serializers.ModelSerializer):
    """Serializer for prompt ratings."""

    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = PromptRating
        fields = [
            'id', 'user', 'user_name', 'rating', 'comment', 'created_at'
        ]
