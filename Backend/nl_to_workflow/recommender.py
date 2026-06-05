"""
Template Recommender for NL to Workflow.

Provides intelligent template recommendations based on:
- Semantic similarity to user description
- User's workflow history
- Popularity and usage patterns
- Domain context
"""

import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from collections import defaultdict

from django.conf import settings

from .vector_store import get_vector_store, search_templates, TemplateVectorStore
from workflows.models import WorkflowTemplate, DomainTemplate, Workflow

logger = logging.getLogger(__name__)


@dataclass
class TemplateRecommendation:
    """A recommended template with scoring."""
    template_id: str
    name: str
    description: str
    category: str
    similarity_score: float
    popularity_score: float
    relevance_score: float
    source: str  # "semantic", "history", "popular", "domain"
    metadata: Dict[str, Any]


class UserHistoryAnalyzer:
    """
    Analyzes user's workflow history to inform recommendations.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_user_categories(self) -> List[str]:
        """Get categories the user frequently uses."""
        try:
            workflows = Workflow.objects.filter(
                owner_id=self.user_id,
                is_active=True
            ).values_list('category', flat=True)[:20]

            return [cat for cat in workflows if cat]

        except Exception as e:
            logger.error(f"Failed to get user categories: {e}")
            return []

    def get_user_node_preferences(self) -> Dict[str, int]:
        """Analyze node type preferences from user's workflows."""
        node_preferences = defaultdict(int)

        try:
            workflows = Workflow.objects.filter(
                owner_id=self.user_id,
                is_active=True
            ).prefetch_related('nodes')

            for workflow in workflows:
                for node in workflow.nodes.all():
                    node_preferences[node.node_type] += 1

            return dict(node_preferences)

        except Exception as e:
            logger.error(f"Failed to analyze node preferences: {e}")
            return {}

    def get_recent_workflow_context(self, limit: int = 5) -> str:
        """Get context from recent workflows."""
        try:
            workflows = Workflow.objects.filter(
                owner_id=self.user_id,
                is_active=True
            ).order_by('-updated_at')[:limit]

            context_parts = []
            for w in workflows:
                if w.description:
                    context_parts.append(w.description)

            return " ".join(context_parts)

        except Exception as e:
            logger.error(f"Failed to get recent workflow context: {e}")
            return ""


class TemplateRecommender:
    """
    Intelligent template recommender.

    Combines multiple signals:
    1. Semantic similarity (vector search)
    2. User history patterns
    3. Popularity metrics
    4. Domain context
    """

    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
        self.vector_store = get_vector_store()
        self.user_analyzer = UserHistoryAnalyzer(user_id) if user_id else None

    def recommend(
        self,
        description: str,
        limit: int = 5,
        include_reasoning: bool = False
    ) -> List[TemplateRecommendation]:
        """
        Get template recommendations for a description.

        Args:
            description: User's workflow description
            limit: Maximum number of recommendations
            include_reasoning: Include reasoning in response

        Returns:
            List of recommendations with scores
        """
        recommendations = []

        # 1. Semantic search
        semantic_results = self._semantic_search(description, limit * 2)
        recommendations.extend(semantic_results)

        # 2. Category-based recommendations
        if self.user_analyzer:
            category_results = self._category_recommendations(description, limit)
            recommendations.extend(category_results)

        # 3. Popular templates
        popular_results = self._popular_recommendations(description, limit)
        recommendations.extend(popular_results)

        # 4. Domain-specific (if applicable)
        domain_results = self._domain_recommendations(description, limit)
        recommendations.extend(domain_results)

        # Deduplicate and rank
        ranked = self._rank_recommendations(recommendations)

        return ranked[:limit]

    def _semantic_search(
        self,
        description: str,
        limit: int
    ) -> List[TemplateRecommendation]:
        """Find templates via semantic similarity."""
        results = self.vector_store.search_similar(
            query=description,
            limit=limit,
            min_similarity=0.3
        )

        recommendations = []
        for r in results:
            recommendations.append(TemplateRecommendation(
                template_id=r['template_id'],
                name=r['name'],
                description=r['description'],
                category=r['category'],
                similarity_score=r['similarity'],
                popularity_score=0.0,
                relevance_score=r['similarity'] * 0.8,  # Weight
                source='semantic',
                metadata=r.get('metadata', {})
            ))

        return recommendations

    def _category_recommendations(
        self,
        description: str,
        limit: int
    ) -> List[TemplateRecommendation]:
        """Recommend based on user's category preferences."""
        if not self.user_analyzer:
            return []

        user_categories = self.user_analyzer.get_user_categories()
        if not user_categories:
            return []

        recommendations = []
        desc_lower = description.lower()

        for category in user_categories:
            # Find templates in user's preferred categories
            templates = WorkflowTemplate.objects.filter(
                category__icontains=category,
                is_active=True
            )[:limit]

            for template in templates:
                # Check if template is relevant to description
                relevance = self._calculate_text_relevance(
                    description,
                    f"{template.name} {template.description}"
                )

                if relevance > 0.2:
                    recommendations.append(TemplateRecommendation(
                        template_id=str(template.id),
                        name=template.name,
                        description=template.description or '',
                        category=template.category or '',
                        similarity_score=relevance,
                        popularity_score=self._get_template_popularity(template),
                        relevance_score=relevance * 0.6,  # Lower weight for category-based
                        source='history',
                        metadata={}
                    ))

        return recommendations

    def _popular_recommendations(
        self,
        description: str,
        limit: int
    ) -> List[TemplateRecommendation]:
        """Recommend popular templates."""
        recommendations = []

        # Get popular templates (could be based on use count, views, etc.)
        templates = WorkflowTemplate.objects.filter(
            is_active=True,
            is_public=True
        ).order_by('-use_count', '-view_count')[:limit * 2]

        for template in templates:
            relevance = self._calculate_text_relevance(
                description,
                f"{template.name} {template.description}"
            )

            if relevance > 0.1:
                popularity = min(template.use_count / 100, 1.0)  # Normalize

                recommendations.append(TemplateRecommendation(
                    template_id=str(template.id),
                    name=template.name,
                    description=template.description or '',
                    category=template.category or '',
                    similarity_score=relevance,
                    popularity_score=popularity,
                    relevance_score=relevance * 0.3 + popularity * 0.2,
                    source='popular',
                    metadata={'use_count': template.use_count}
                ))

        return recommendations

    def _domain_recommendations(
        self,
        description: str,
        limit: int
    ) -> List[TemplateRecommendation]:
        """Recommend based on domain templates."""
        recommendations = []

        # Detect domain from description
        domain = self._detect_domain(description)
        if not domain:
            return []

        # Get domain templates
        domain_templates = DomainTemplate.objects.filter(
            domain__icontains=domain,
            is_active=True
        ).order_by('-use_count')[:limit]

        for template in domain_templates:
            relevance = self._calculate_text_relevance(
                description,
                f"{template.name} {template.description}"
            )

            recommendations.append(TemplateRecommendation(
                template_id=str(template.id),
                name=template.name,
                description=template.description or '',
                category=domain,
                similarity_score=relevance,
                popularity_score=min(template.use_count / 50, 1.0),
                relevance_score=relevance * 0.5 + 0.3,  # Domain boost
                source='domain',
                metadata={'domain': domain, 'use_count': template.use_count}
            ))

        return recommendations

    def _rank_recommendations(
        self,
        recommendations: List[TemplateRecommendation]
    ) -> List[TemplateRecommendation]:
        """Rank and deduplicate recommendations."""
        # Deduplicate by template_id
        seen = {}
        for rec in recommendations:
            if rec.template_id not in seen:
                seen[rec.template_id] = rec
            else:
                # Keep highest score
                existing = seen[rec.template_id]
                if rec.relevance_score > existing.relevance_score:
                    seen[rec.template_id] = rec

        # Sort by relevance score
        ranked = list(seen.values())
        ranked.sort(key=lambda x: x.relevance_score, reverse=True)

        return ranked

    def _calculate_text_relevance(
        self,
        query: str,
        text: str,
        threshold: float = 0.1
    ) -> float:
        """Calculate simple text relevance score."""
        query_lower = query.lower()
        text_lower = text.lower()

        # Tokenize
        query_words = set(query_lower.split())
        text_words = set(text_lower.split())

        # Remove common words
        stop_words = {'的', '了', '和', '是', '在', '我', '有', '个', '要', '你', 'the', 'a', 'an', 'is', 'are'}
        query_words -= stop_words
        text_words -= stop_words

        if not query_words:
            return 0.0

        # Jaccard similarity
        intersection = len(query_words & text_words)
        union = len(query_words | text_words)

        if union == 0:
            return 0.0

        similarity = intersection / union

        # Boost for exact phrase matches
        if query_lower in text_lower:
            similarity = min(similarity + 0.3, 1.0)

        return max(similarity, 0.0)

    def _detect_domain(self, description: str) -> Optional[str]:
        """Detect domain from description."""
        desc_lower = description.lower()

        domain_keywords = {
            'customer_service': ['客服', '客户', '服务', '售后', 'customer', 'service', 'support'],
            'data_processing': ['数据', '处理', 'ETL', '清洗', 'data', 'process', 'pipeline'],
            'content_generation': ['内容', '文章', '生成', '创作', 'content', 'article', 'generate'],
            'moderation': ['审核', '内容审核', '过滤', 'moderation', 'filter'],
            'translation': ['翻译', '多语言', 'translation', 'language'],
            'analytics': ['分析', '统计', '报表', 'analytics', 'report', 'statistics'],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in desc_lower for kw in keywords):
                return domain

        return None

    def _get_template_popularity(self, template: WorkflowTemplate) -> float:
        """Get normalized popularity score for template."""
        # Combine various metrics
        use_score = min(template.use_count / 100, 1.0)
        view_score = min(getattr(template, 'view_count', 0) / 500, 1.0)

        return (use_score * 0.7 + view_score * 0.3)


class RecommendationContextBuilder:
    """
    Builds context for LLM with template recommendations.
    """

    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
        self.recommender = TemplateRecommender(user_id)

    def build_context(
        self,
        description: str,
        limit: int = 3
    ) -> str:
        """
        Build context string for LLM with recommended templates.

        Args:
            description: User's description
            limit: Number of templates to include

        Returns:
            Context string with template recommendations
        """
        recommendations = self.recommender.recommend(description, limit=limit)

        if not recommendations:
            return ""

        context_parts = ["\n\n## 相关模板参考\n"]
        context_parts.append("以下模板可能与您的需求相关，可作为参考：\n")

        for i, rec in enumerate(recommendations, 1):
            context_parts.append(f"### {i}. {rec.name}")
            context_parts.append(f"- 类型: {rec.category}")
            context_parts.append(f"- 描述: {rec.description}")
            context_parts.append(f"- 相关度: {rec.relevance_score:.0%}")

            # Add metadata if available
            if rec.metadata:
                if 'use_count' in rec.metadata:
                    context_parts.append(f"- 使用次数: {rec.metadata['use_count']}")

            context_parts.append("")

        return "\n".join(context_parts)


def get_recommendations(
    description: str,
    user_id: Optional[int] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Convenience function to get template recommendations.

    Args:
        description: User's workflow description
        user_id: Optional user ID for personalized recommendations
        limit: Maximum recommendations

    Returns:
        List of recommendation dicts
    """
    recommender = TemplateRecommender(user_id)
    recommendations = recommender.recommend(description, limit=limit)

    return [
        {
            'template_id': r.template_id,
            'name': r.name,
            'description': r.description,
            'category': r.category,
            'similarity': r.similarity_score,
            'relevance': r.relevance_score,
            'source': r.source,
        }
        for r in recommendations
    ]


def build_recommendation_context(
    description: str,
    user_id: Optional[int] = None,
    limit: int = 3
) -> str:
    """
    Build context string with recommendations for LLM.

    Args:
        description: User's description
        user_id: Optional user ID
        limit: Number of templates

    Returns:
        Context string
    """
    builder = RecommendationContextBuilder(user_id)
    return builder.build_context(description, limit)
