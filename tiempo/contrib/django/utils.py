from django.conf import settings
from tiempo.conf import DEBUG

import chalk
import importlib


def auto_load_tasks():
    for app in settings.PROJECT_APPS:
        module = importlib.import_module(app)
        try:
            importlib.import_module(app + '.tasks')
            chalk.blue('imported tasks from %s' % app)
        except ImportError as e:
            # print traceback.format_exc()
            pass
    if DEBUG:
        pass
        # import tasks
