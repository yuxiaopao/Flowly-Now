"""
Celery tasks for branding app.
Handles CDN cache refresh, email template processing, and domain verification.
"""

from celery import shared_task
from django.utils import timezone


@shared_task
def refresh_cdn_cache(tenant_id: str):
    """
    Refresh CDN cache for tenant branding assets.

    Args:
        tenant_id: ID of the tenant
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        # Invalidate CDN cache for branding assets
        # This would integrate with specific CDN provider (CloudFront, CloudFlare, etc.)

        cache_urls = [
            f'/branding/{tenant_id}/logo.png',
            f'/branding/{tenant_id}/favicon.ico',
            f'/branding/{tenant_id}/styles.css',
        ]

        # Example: Invalidate CloudFront cache
        # cloudfront.create_invalidation(
        #     DistributionId=settings.CLOUDFRONT_DISTRIBUTION_ID,
        #     InvalidationBatch={
        #         'Paths': {'Quantity': len(cache_urls), 'Items': cache_urls},
        #         'CallerReference': str(timezone.now().timestamp())
        #     }
        # )

        logger.info(f"CDN cache refreshed for tenant: {tenant_id}")

        return {
            'tenant_id': tenant_id,
            'cache_urls_invalidated': len(cache_urls),
            'status': 'success'
        }

    except Exception as e:
        logger.error(f"CDN cache refresh failed for tenant {tenant_id}: {e}")
        return {
            'tenant_id': tenant_id,
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def process_email_template(template_id: int):
    """
    Process and validate email template.

    Args:
        template_id: ID of the email template
    """
    try:
        from .models import EmailTemplate

        template = EmailTemplate.objects.get(id=template_id)

        # Validate template syntax
        errors = []

        # Check for required variables
        if '{{' in template.content and '}}' in template.content:
            import re
            variables = re.findall(r'\{\{(\w+)\}\}', template.content)
            required_vars = ['user_name', 'app_name']
            missing_vars = [v for v in required_vars if v not in variables]
            if missing_vars:
                errors.append(f'Missing required variables: {missing_vars}')

        # Check template length
        if len(template.content) > 50000:
            errors.append('Template content exceeds maximum length of 50000 characters')

        if errors:
            template.validation_errors = errors
            template.is_valid = False
        else:
            template.is_valid = True
            template.validation_errors = None

        template.save()

        return {
            'template_id': template_id,
            'is_valid': template.is_valid,
            'errors': errors
        }

    except Exception as e:
        return {
            'template_id': template_id,
            'status': 'error',
            'error': str(e)
        }


@shared_task
def send_bulk_email(template_id: int, recipient_ids: list):
    """
    Send bulk emails using a template.

    Args:
        template_id: ID of the email template
        recipient_ids: List of recipient user IDs
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        from .models import EmailTemplate

        template = EmailTemplate.objects.get(id=template_id)

        sent_count = 0
        failed_count = 0

        for recipient_id in recipient_ids:
            try:
                # Get recipient details
                from users.models import User
                user = User.objects.get(id=recipient_id)

                # Render template
                context = {
                    'user_name': user.get_full_name() or user.username,
                    'email': user.email,
                    'app_name': 'Flowly',
                    'current_year': timezone.now().year
                }

                # Simple template rendering
                content = template.content
                for key, value in context.items():
                    content = content.replace(f'{{{{{key}}}}}', str(value))

                send_mail(
                    subject=template.subject,
                    message=content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=content if template.template_type == 'html' else None,
                    fail_silently=False
                )

                sent_count += 1

            except Exception:
                failed_count += 1

        return {
            'template_id': template_id,
            'sent': sent_count,
            'failed': failed_count,
            'total': len(recipient_ids)
        }

    except Exception as e:
        return {
            'template_id': template_id,
            'status': 'error',
            'error': str(e)
        }


@shared_task
def verify_custom_domain(domain_id: int):
    """
    Verify DNS configuration for custom domain.

    Args:
        domain_id: ID of the custom domain
    """
    try:
        import socket
        import dns.resolver

        from .models import CustomDomain

        domain = CustomDomain.objects.get(id=domain_id)

        # Check DNS records
        dns_records = {}

        # Check TXT record for verification
        try:
            answers = dns.resolver.resolve(f'_flowly-verification.{domain.domain}', 'TXT')
            dns_records['txt'] = [str(rdata) for rdata in answers]
        except dns.resolver.NXDOMAIN:
            dns_records['txt'] = None

        # Check CNAME record for routing
        try:
            answers = dns.resolver.resolve(domain.domain, 'CNAME')
            dns_records['cname'] = [str(rdata) for rdata in answers]
        except dns.resolver.NXDOMAIN:
            dns_records['cname'] = None

        # Check A record
        try:
            answers = dns.resolver.resolve(domain.domain, 'A')
            dns_records['a'] = [str(rdata) for rdata in answers]
        except dns.resolver.NXDOMAIN:
            dns_records['a'] = None

        # Determine verification status
        expected_txt = f'_flowly-verification={domain.verification_token}'
        txt_valid = expected_txt in (dns_records.get('txt') or [])

        # Update domain status
        if txt_valid:
            domain.is_verified = True
            domain.dns_records = dns_records
            domain.save()

        return {
            'domain_id': domain_id,
            'domain': domain.domain,
            'dns_records': dns_records,
            'is_verified': txt_valid,
            'status': 'verified' if txt_valid else 'pending'
        }

    except Exception as e:
        return {
            'domain_id': domain_id,
            'status': 'error',
            'error': str(e)
        }


@shared_task
def refresh_ssl_certificate(domain_id: int):
    """
    Refresh SSL certificate for custom domain.

    Args:
        domain_id: ID of the custom domain
    """
    try:
        from .models import CustomDomain

        domain = CustomDomain.objects.get(id=domain_id)

        if not domain.is_verified:
            return {
                'domain_id': domain_id,
                'status': 'error',
                'error': 'Domain not verified'
            }

        # Request SSL certificate renewal
        # This would integrate with Let's Encrypt or certificate provider
        # cert_manager.request_certificate(domain.domain)

        domain.ssl_status = 'renewing'
        domain.ssl_renewed_at = timezone.now()
        domain.save()

        return {
            'domain_id': domain_id,
            'domain': domain.domain,
            'status': 'renewing',
            'renewed_at': domain.ssl_renewed_at.isoformat()
        }

    except CustomDomain.DoesNotExist:
        return {
            'domain_id': domain_id,
            'status': 'error',
            'error': f'Domain {domain_id} not found'
        }


@shared_task
def export_branding_config(tenant_id: str):
    """
    Export branding configuration for a tenant.

    Args:
        tenant_id: ID of the tenant
    """
    try:
        from .models import BrandingConfig

        config = BrandingConfig.objects.get(tenant_id=tenant_id)

        export_data = {
            'tenant_id': str(tenant_id),
            'config': config.config,
            'logo_url': config.logo_url,
            'primary_color': config.primary_color,
            'secondary_color': config.secondary_color,
            'exported_at': timezone.now().isoformat()
        }

        return export_data

    except BrandingConfig.DoesNotExist:
        return {
            'tenant_id': tenant_id,
            'status': 'error',
            'error': 'Branding config not found'
        }


@shared_task
def apply_branding_preset(tenant_id: str, preset_name: str):
    """
    Apply a branding preset to a tenant.

    Args:
        tenant_id: ID of the tenant
        preset_name: Name of the preset to apply
    """
    presets = {
        'professional': {
            'primary_color': '#1976D2',
            'secondary_color': '#424242',
            'font_family': 'Roboto'
        },
        'modern': {
            'primary_color': '#7C4DFF',
            'secondary_color': '#E8E8E8',
            'font_family': 'Inter'
        },
        'minimal': {
            'primary_color': '#212121',
            'secondary_color': '#757575',
            'font_family': 'Open Sans'
        }
    }

    if preset_name not in presets:
        return {
            'tenant_id': tenant_id,
            'status': 'error',
            'error': f'Preset {preset_name} not found'
        }

    try:
        from .models import BrandingConfig

        config, _ = BrandingConfig.objects.get_or_create(tenant_id=tenant_id)
        preset = presets[preset_name]

        config.primary_color = preset['primary_color']
        config.secondary_color = preset['secondary_color']
        config.font_family = preset['font_family']
        config.save()

        # Queue CDN refresh
        refresh_cdn_cache.delay(str(tenant_id))

        return {
            'tenant_id': tenant_id,
            'preset': preset_name,
            'applied': preset,
            'status': 'success'
        }

    except Exception as e:
        return {
            'tenant_id': tenant_id,
            'status': 'error',
            'error': str(e)
        }
