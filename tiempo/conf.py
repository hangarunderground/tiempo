from logging import getLogger
import os
from tiempo import LEAVE_DJANGO_UNSET

logger = getLogger(__name__)

try:
    from django.conf import settings
    has_django = True
except (ImportError, Exception), e:
    logger.warning(str(e))
    has_django = False

import json


if has_django and not LEAVE_DJANGO_UNSET:
    INTERVAL = getattr(settings, 'TIEMPO_INTERVAL', 5)
    THREAD_CONFIG = getattr(settings, 'TIEMPO_THREAD_CONFIG', [('1','2','3'),('1','2'),('1',)])
    RESULT_LIFESPAN = getattr(settings, 'TIEMPO_RESULT_LIFESPAN_DAYS', 1)
    DEBUG = settings.DEBUG

    REDIS_HOST = getattr(settings,'REDIS_HOST', None) or 'localhost'
    REDIS_PORT = getattr(settings, 'REDIS_PORT', None) or '6379'
    REDIS_QUEUE_DB = getattr(settings, 'REDIS_QUEUE_DB', None) or 7
    REDIS_TEST_DB = getattr(settings, 'REDIS_QUEUE_DB', None) or 13
    REDIS_PW = getattr(settings, 'REDIS_PW', None)
    SCHEDULE_AHEAD_MINUTES = getattr(settings, 'SCHEDULE_AHEAD_MINUTES', 180)
    MAX_SCHEDULE_AHEAD_JOBS = getattr(settings, 'MAX_SCHEDULE_AHEAD_JOBS', 100)
else:
    INTERVAL = os.environ.get('TIEMPO_INTERVAL', 1)
    THREAD_CONFIG = os.environ.get('THREAD_CONFIG', [('1','2','3'),('1','2'),('1',)])
    RESULT_LIFESPAN = os.environ.get('TIEMPO_RESULT_LIFESPAN_DAYS', 1)
    DEBUG = os.environ.get('TIEMPO_DEBUG', False)

    REDIS_HOST = os.environ.get('TIEMPO_REDIS_HOST', 'localhost')
    REDIS_PORT = os.environ.get('TIEMPO_REDIS_PORT', 6379)
    REDIS_QUEUE_DB = os.environ.get('TIEMPO_REDIS_QUEUE_DB', 12)
    REDIS_TEST_DB = os.environ.get('TIEMPO_REDIS_TEST_DB', 13)
    REDIS_PW = os.environ.get('TIEMPO_REDIS_PW', None)
    SCHEDULE_AHEAD_MINUTES = os.environ.get('SCHEDULE_AHEAD_MINUTES', 180)
    MAX_SCHEDULE_AHEAD_JOBS = os.environ.get('MAX_SCHEDULE_AHEAD_JOBS', 100)

TASK_PATHS = json.loads(os.environ.get('TIEMPO_TASK_PATHS', '["tiempo.demo"]'))
