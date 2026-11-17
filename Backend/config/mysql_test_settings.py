"""Optional ORM regression profile for an explicitly provisioned local test MySQL."""
import os

from .project_test_settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '127.0.0.1',
        'PORT': os.environ['FLOWLY_TEST_MYSQL_PORT'],
        'USER': os.getenv('FLOWLY_TEST_MYSQL_USER', 'root'),
        'PASSWORD': os.environ['FLOWLY_TEST_MYSQL_PASSWORD'],
        'NAME': 'flowly_isolated_qa',
        'TEST': {'NAME': 'test_flowly_isolated_qa'},
        'OPTIONS': {'charset': 'utf8mb4', 'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"},
    },
}
