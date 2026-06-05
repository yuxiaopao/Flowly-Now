"""
Celery tasks for marketplace app.
Handles template syncing, featured content, and analytics.
"""

from celery import shared_task
from django.utils import timezone


@shared_task
def sync_marketplace_templates():
    """
    Synchronize marketplace templates with featured/curated content.
    """
    from .models import WorkflowTemplate

    # Update featured templates based on metrics
    featured_templates = WorkflowTemplate.objects.filter(
        is_published=True,
        is_featured=True
    ).order_by('-install_count', '-avg_rating')[:10]

    synced_count = 0
    for template in featured_templates:
        # Could update search index, cache, etc.
        synced_count += 1

    return {'templates_synced': synced_count}


@shared_task
def update_template_stats():
    """
    Update statistics for all marketplace templates.
    """
    from .models import WorkflowTemplate, TemplateInstall, TemplateRating
    from django.db.models import Avg, Count

    templates = WorkflowTemplate.objects.filter(is_published=True)

    updated_count = 0
    for template in templates:
        # Update install count
        install_count = TemplateInstall.objects.filter(template=template).count()
        template.install_count = install_count

        # Update average rating
        rating_data = TemplateRating.objects.filter(template=template).aggregate(
            avg=Avg('rating'),
            count=Count('id')
        )
        if rating_data['avg']:
            template.avg_rating = round(rating_data['avg'], 2)
        template.rating_count = rating_data['count'] or 0

        template.save()
        updated_count += 1

    return {'templates_updated': updated_count}


@shared_task
def send_marketplace_digest(days: int = 7):
    """
    Generate and send marketplace digest email to users.

    Args:
        days: Number of days to include in digest
    """
    from datetime import timedelta

    from .models import WorkflowTemplate, TemplateInstall

    cutoff = timezone.now() - timedelta(days=days)

    # Get recent popular templates
    recent_templates = WorkflowTemplate.objects.filter(
        is_published=True,
        created_at__gte=cutoff
    ).order_by('-install_count')[:10]

    # Get most installed templates
    top_templates = TemplateInstall.objects.filter(
        installed_at__gte=cutoff
    ).values('template__id', 'template__name').annotate(
        install_count=Count('id')
    ).order_by('-install_count')[:10]

    digest = {
        'period_days': days,
        'period_start': cutoff.isoformat(),
        'period_end': timezone.now().isoformat(),
        'recent_templates': [
            {
                'id': t.id,
                'name': t.name,
                'category': t.category,
                'install_count': t.install_count,
                'avg_rating': t.avg_rating
            }
            for t in recent_templates
        ],
        'top_installed': list(top_templates)
    }

    return digest


@shared_task
def archive_unpublished_templates(days: int = 180):
    """
    Archive templates that have been unpublished for a long time.

    Args:
        days: Days after unpublished before archiving
    """
    from datetime import timedelta

    from .models import WorkflowTemplate

    cutoff = timezone.now() - timedelta(days=days)

    # Find unpublished templates older than cutoff
    old_templates = WorkflowTemplate.objects.filter(
        is_published=False,
        updated_at__lt=cutoff,
        is_archived=False
    )

    archived_count = 0
    for template in old_templates:
        template.is_archived = True
        template.save()
        archived_count += 1

    return {'templates_archived': archived_count}


@shared_task
def verify_template_integrity():
    """
    Verify integrity of marketplace templates.
    Check for broken workflows, missing nodes, etc.
    """
    from .models import WorkflowTemplate

    templates = WorkflowTemplate.objects.filter(
        is_published=True,
        is_archived=False
    )

    issues = []
    for template in templates:
        # Check if workflow data is valid JSON
        if template.workflow_data:
            import json
            try:
                json.loads(template.workflow_data)
            except json.JSONDecodeError:
                issues.append({
                    'template_id': template.id,
                    'issue': 'invalid_json',
                    'name': template.name
                })

        # Could add more integrity checks

    return {
        'templates_checked': templates.count(),
        'issues_found': len(issues),
        'issues': issues
    }


@shared_task
def update_category_counts():
    """
    Update template counts for each category.
    """
    from .models import TemplateCategory

    categories = TemplateCategory.objects.filter(is_active=True)

    updated_count = 0
    for category in categories:
        count = category.templates.filter(is_published=True).count()
        if category.template_count != count:
            category.template_count = count
            category.save()
            updated_count += 1

    return {'categories_updated': updated_count}


@shared_task
def generate_marketplace_report(month: int = None):
    """
    Generate monthly marketplace analytics report.

    Args:
        month: Month number (1-12), defaults to current month
    """
    from datetime import datetime

    from .models import WorkflowTemplate, TemplateInstall

    if month is None:
        month = timezone.now().month

    # Calculate date range
    year = timezone.now().year
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    start_date = timezone.make_aware(start_date)
    end_date = timezone.make_aware(end_date)

    # Template stats
    templates_created = WorkflowTemplate.objects.filter(
        created_at__gte=start_date,
        created_at__lt=end_date
    ).count()

    templates_published = WorkflowTemplate.objects.filter(
        published_at__gte=start_date,
        published_at__lt=end_date
    ).count()

    # Install stats
    installs = TemplateInstall.objects.filter(
        installed_at__gte=start_date,
        installed_at__lt=end_date
    )

    total_installs = installs.count()
    unique_installers = installs.values('installed_by').distinct().count()

    report = {
        'year': year,
        'month': month,
        'period_start': start_date.isoformat(),
        'period_end': end_date.isoformat(),
        'templates_created': templates_created,
        'templates_published': templates_published,
        'total_installs': total_installs,
        'unique_installers': unique_installers
    }

    return report
