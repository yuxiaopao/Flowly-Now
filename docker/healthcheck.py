"""Check the local API with a configured Host header and no redirect following."""

import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_URL = 'http://127.0.0.1:8000/api/health/'
DEFAULT_TIMEOUT_SECONDS = 5


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def health_host(environment):
    explicit = environment.get('HEALTHCHECK_HOST', '').strip()
    allowed = [host.strip().lstrip('.') for host in environment.get('ALLOWED_HOSTS', '').split(',') if host.strip()]
    host = explicit or (allowed[0] if allowed else '127.0.0.1')
    return '127.0.0.1' if host == '*' else host


def healthy(url, host, timeout=DEFAULT_TIMEOUT_SECONDS):
    try:
        request = Request(url, headers={'Host': host})
        with build_opener(NoRedirect).open(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def main():
    timeout = float(os.environ.get('HEALTHCHECK_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS))
    if timeout <= 0:
        return 1
    return 0 if healthy(os.environ.get('HEALTHCHECK_URL', DEFAULT_URL), health_host(os.environ), timeout) else 1


if __name__ == '__main__':
    sys.exit(main())
