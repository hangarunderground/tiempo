PROJECT_PATH = __path__[0]

TIEMPO_REGISTRY = {}

# RUNNERS here is used as a global singleton. By default, instances of
# tiempo.runner.Runner add themselves as values for keys matching their groups.
RUNNERS = {}

def all_runners():
    all_runners = set()
    for runner_list in RUNNERS.values():
        for runner in runner_list:
            all_runners.add(runner)

    return all_runners


REDIS_GROUP_NAMESPACE = 'tiempogroup'
RECENT_KEY = 'tiempo:recent_tasks'
RESULT_PREFIX = 'tiempo:task_result'
LEAVE_DJANGO_UNSET = False  # Don't use django settings during loop start.

__version__ = "1.1.8"
