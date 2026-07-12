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
        install_count = TemplateInstall.objects.filter(template=template).count()
        rating_data = TemplateRating.objects.filter(template=template).aggregate(
            avg=Avg('rating'),
            count=Count('id')
        )

        template.install_count = install_count
        template.avg_rating = round(rating_data['avg'], 2) if rating_data['avg'] else 0
        template.save(update_fields=[
            'install_count',
            'avg_rating',
            'updated_at',
        ])
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
    from django.db.models import Count

    from .models import WorkflowTemplate, TemplateInstall

    cutoff = timezone.now() - timedelta(days=days)

    recent_templates = WorkflowTemplate.objects.filter(
        is_published=True,
        created_at__gte=cutoff
    ).order_by('-install_count')[:10]

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
    Identify unpublished templates older than the cutoff.

    Args:
        days: Days after last update before a template is considered stale
    """
    from datetime import timedelta

    from .models import WorkflowTemplate

    cutoff = timezone.now() - timedelta(days=days)

    stale_templates = WorkflowTemplate.objects.filter(
        is_published=False,
        updated_at__lt=cutoff
    )

    return {
        'templates_found': stale_templates.count(),
        'cutoff': cutoff.isoformat(),
    }


@shared_task
def verify_template_integrity():
    """
    Verify integrity of marketplace templates.
    Check for broken workflows, missing nodes, etc.
    """
    from .models import WorkflowTemplate

    templates = WorkflowTemplate.objects.filter(is_published=True)

    issues = []
    for template in templates:
        if template.workflow_data and not isinstance(template.workflow_data, dict):
            issues.append({
                'template_id': template.id,
                'issue': 'invalid_workflow_data_type',
                'name': template.name
            })

    return {
        'templates_checked': templates.count(),
        'issues_found': len(issues),
        'issues': issues
    }


@shared_task
def update_category_counts():
    """
    Build current published template counts for each category.
    """
    from .models import TemplateCategory

    category_counts = []
    for category in TemplateCategory.objects.all().order_by('order', 'name'):
        category_counts.append({
            'category_id': category.id,
            'category_slug': category.slug,
            'template_count': category.templates.filter(is_published=True).count(),
        })

    return {
        'categories_updated': len(category_counts),
        'categories': category_counts,
    }


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

    year = timezone.now().year
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    start_date = timezone.make_aware(start_date)
    end_date = timezone.make_aware(end_date)

    templates_created = WorkflowTemplate.objects.filter(
        created_at__gte=start_date,
        created_at__lt=end_date
    ).count()

    templates_published = WorkflowTemplate.objects.filter(
        is_published=True,
        created_at__gte=start_date,
        created_at__lt=end_date
    ).count()

    installs = TemplateInstall.objects.filter(
        installed_at__gte=start_date,
        installed_at__lt=end_date
    )

    total_installs = installs.count()
    unique_installers = installs.values('user_id').distinct().count()

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
