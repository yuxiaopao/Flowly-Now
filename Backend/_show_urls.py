import os, sys
sys.path.insert(0, 'e:/Flowly-now/Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.urls import reverse
from django.urls.resolvers import URLResolver, URLPattern

def show_urls(urlpatterns, prefix=''):
    for pattern in urlpatterns:
        if isinstance(pattern, URLResolver):
            show_urls(pattern.url_patterns, prefix + str(pattern.pattern))
        elif isinstance(pattern, URLPattern):
            print(f'{prefix}{pattern.pattern} -> {pattern.name or "unnamed"}')

show_urls(__import__('config.urls', fromlist=['urlpatterns']).urlpatterns)
