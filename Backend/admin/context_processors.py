"""Admin template context processors."""

from django.conf import settings

from admin.constants import (
    PLATFORM_ADMIN_TITLE,
    PLATFORM_SITE_NAME,
    PLATFORM_SITE_TAGLINE,
)


def flowly_admin(request):
    """Inject Flowly admin URLs and site name into all templates."""
    site_name = PLATFORM_SITE_NAME
    try:
        from admin.services.config_service import get_public_config
        public = get_public_config()
        site_name = public.get('site', {}).get('name') or public.get('site_name') or site_name
    except Exception:
        pass

    return {
        'frontend_url': getattr(settings, 'FRONTEND_URL', 'http://localhost:5200').rstrip('/'),
        'site_name': site_name,
        'platform_admin_title': PLATFORM_ADMIN_TITLE,
        'site_tagline': PLATFORM_SITE_TAGLINE,
    }
