"""Resilient email delivery with console-backend fallback for local/dev."""

import logging

from django.conf import settings
from django.core.mail import get_connection, send_mail

logger = logging.getLogger(__name__)

CONSOLE_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


def send_email_with_fallback(subject, message, recipient_list, from_email=None):
    """Send email via configured backend; on SMTP failure retry with console backend.

    Returns True when the message was handed off to any backend successfully.
    """
    from_email = from_email or settings.DEFAULT_FROM_EMAIL
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        return True
    except Exception as smtp_exc:
        if getattr(settings, 'EMAIL_BACKEND', '') == CONSOLE_EMAIL_BACKEND:
            logger.error("Console email delivery failed: %s", smtp_exc)
            return False
        logger.warning(
            "Primary email backend failed (%s); retrying with console backend",
            smtp_exc,
        )
        try:
            connection = get_connection(backend=CONSOLE_EMAIL_BACKEND, fail_silently=False)
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                connection=connection,
                fail_silently=False,
            )
            return True
        except Exception as console_exc:
            logger.error(
                "Email delivery failed for %s (SMTP: %s; console: %s)",
                recipient_list,
                smtp_exc,
                console_exc,
            )
            return False
