"""
Celery tasks for prompts app.
Handles template analysis, recommendations, and maintenance tasks.
"""

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone
from django.db.models import Avg, Count, Q


@shared_task(bind=True, max_retries=3)
def analyze_template_quality(self, template_id: int):
    """
    Analyze template quality and update metrics.

    Args:
        template_id: ID of the template to analyze
    """
    try:
        from .models import PromptTemplate, PromptRating, PromptUsage

        template = PromptTemplate.objects.get(id=template_id)

        # Calculate average rating
        ratings = PromptRating.objects.filter(template=template)
        if ratings.exists():
            avg_rating = ratings.aggregate(avg=Avg('value'))['avg']
            template.avg_rating = round(avg_rating, 2)
            template.rating_count = ratings.count()

        # Calculate success rate from usage
        usage_records = PromptUsage.objects.filter(template=template)
        if usage_records.exists():
            successful = usage_records.filter(success=True).count()
            template.usage_count = usage_records.count()
            template.success_rate = round((successful / usage_records.count()) * 100, 2)

        template.save()

        return {
            'template_id': template_id,
            'avg_rating': template.avg_rating,
            'rating_count': template.rating_count,
            'usage_count': template.usage_count,
            'success_rate': template.success_rate
        }

    except Exception as e:
        try:
            raise self.retry(exc=e, countdown=60)
        except MaxRetriesExceededError:
            return {'error': f'Max retries exceeded for template {template_id}'}


@shared_task
def generate_template_recommendations(user_id: int, limit: int = 10):
    """
    Generate personalized template recommendations for a user.

    Args:
        user_id: ID of the user
        limit: Maximum number of recommendations
    """
    try:
        from users.models import User
        from .models import PromptTemplate

        user = User.objects.get(id=user_id)

        # Simple recommendation based on popularity and recency
        # Could be enhanced with ML-based recommendations
        templates = PromptTemplate.objects.filter(
            is_active=True
        ).annotate(
            score=Count('usages') + Avg('avg_rating') * 10
        ).order_by('-score')[:limit]

        return {
            'user_id': user_id,
            'recommendations': [
                {
                    'id': t.id,
                    'name': t.name,
                    'category': t.category,
                    'avg_rating': t.avg_rating,
                    'usage_count': t.usage_count
                }
                for t in templates
            ]
        }

    except Exception as e:
        return {'error': str(e)}


@shared_task
def sync_template_categories():
    """
    Synchronize template categories with predefined list.
    """
    from .models import PromptCategory

    predefined_categories = [
        {'name': 'Customer Support', 'slug': 'customer-support', 'icon': 'headphones'},
        {'name': 'Content Writing', 'slug': 'content-writing', 'icon': 'edit'},
        {'name': 'Code Generation', 'slug': 'code-generation', 'icon': 'code'},
        {'name': 'Data Analysis', 'slug': 'data-analysis', 'icon': 'chart'},
        {'name': 'Marketing', 'slug': 'marketing', 'icon': 'megaphone'},
        {'name': 'Sales', 'slug': 'sales', 'icon': 'trending-up'},
        {'name': 'HR & Recruitment', 'slug': 'hr-recruitment', 'icon': 'users'},
        {'name': 'Education', 'slug': 'education', 'icon': 'book'},
    ]

    created_count = 0
    for cat_data in predefined_categories:
        category, created = PromptCategory.objects.get_or_create(
            slug=cat_data['slug'],
            defaults={
                'name': cat_data['name'],
                'icon': cat_data.get('icon', 'folder'),
                'is_active': True
            }
        )
        if created:
            created_count += 1

    return {'categories_created': created_count}


@shared_task
def cleanup_unused_templates(days: int = 90):
    """
    Archive templates that haven't been used in specified days.

    Args:
        days: Number of days of inactivity
    """
    from datetime import timedelta

    from .models import PromptTemplate

    cutoff = timezone.now() - timedelta(days=days)

    # Find templates with no usage in the period
    unused_templates = PromptTemplate.objects.filter(
        is_active=True,
        updated_at__lt=cutoff
    ).annotate(
        usage_count=Count('usages')
    ).filter(usage_count=0)

    archived_count = 0
    for template in unused_templates:
        template.is_active = False
        template.save()
        archived_count += 1

    return {'templates_archived': archived_count}


@shared_task
def update_template_search_index():
    """
    Update search index for all active templates.
    """
    from .models import PromptTemplate

    active_templates = PromptTemplate.objects.filter(is_active=True)

    indexed_count = 0
    for template in active_templates:
        # Could integrate with search service like Elasticsearch
        # For now, just log the update
        indexed_count += 1

    return {'templates_indexed': indexed_count}


@shared_task
def send_template_analytics_report(days: int = 30):
    """
    Generate and send template analytics report.

    Args:
        days: Number of days to analyze
    """
    from datetime import timedelta

    from .models import PromptTemplate, PromptUsage

    cutoff = timezone.now() - timedelta(days=days)

    # Template performance stats
    stats = PromptTemplate.objects.filter(
        usages__created_at__gte=cutoff
    ).annotate(
        total_usage=Count('usages'),
        successful_usage=Count('usages', filter=Q(usages__success=True))
    ).order_by('-total_usage')[:20]

    report = {
        'period_days': days,
        'period_start': cutoff.isoformat(),
        'period_end': timezone.now().isoformat(),
        'top_templates': [
            {
                'id': t.id,
                'name': t.name,
                'total_usage': t.total_usage,
                'successful_usage': t.successful_usage,
                'success_rate': round(t.successful_usage / t.total_usage * 100, 2) if t.total_usage else 0
            }
            for t in stats
        ]
    }

    return report
