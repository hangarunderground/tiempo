try:
    from django.conf import settings
    has_django = True
except ImportError:
    import os.environ as env
    has_django = False


if has_django:
    INTERVAL = getattr(settings, 'TIEMPO_INTERVAL', 5)
    THREAD_COUNT = getattr(settings, 'TIEMPO_THREADS', 1)
    TASK_GROUPS = ['ALL'] + getattr(settings, 'TIEMPO_GROUPS', [])
    RESULT_LIFESPAN = getattr(settings, 'TIEMPO_RESULT_LIFESPAN_DAYS', 1)
    DEBUG = settings.DEBUG

    REDIS_HOST = settings.REDIS_HOST
    REDIS_PORT = settings.REDIS_PORT
    REDIS_QUEUE_DB = settings.REDIS_QUEUE_DB
    REDIS_PW = settings.REDIS_PW

else:
    INTERVAL = env.get('TIEMPO_INTERVAL', 5)
    THREAD_COUNT = env.get('TIEMPO_THREADS', 1)
    TASK_GROUPS = ['ALL'] + env.get('TIEMPO_GROUPS', [])
    RESULT_LIFESPAN = env.get('TIEMPO_RESULT_LIFESPAN_DAYS', 1)
    DEBUG = env.get('TIEMPO_DEBUG', False)

    REDIS_HOST = env.get('TIEMPO_REDIS_HOST', 'localhost')
    REDIS_PORT = env.get('TIEMPO_REDIS_PORT', 6379)
    REDIS_QUEUE_DB = env.get('TIEMPO_REDIS_QUEUE_DB', 12)
    REDIS_PW = env.get('TIEMPO_REDIS_PW', None)
