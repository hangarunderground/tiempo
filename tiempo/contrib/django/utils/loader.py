from django.conf import settings
from tiempo.conf import DEBUG

import chalk
import importlib


def auto_load_tasks():
    for app in settings.INSTALLED_APPS:
        module = importlib.import_module(app)
        try:
            importlib.import_module(app + '.tasks')
            chalk.blue('imported tasks from %s' % app)
        except ImportError as e:
            if not e.args[0] == 'No module named tasks':
                raise
    if DEBUG:
        pass
        # import tasks
