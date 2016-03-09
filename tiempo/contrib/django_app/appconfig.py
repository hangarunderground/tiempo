import os
import sys

from tiempo.execution import thread_init
from .utils.loader import auto_load_tasks
from django.apps import AppConfig, apps
from django.conf import settings


class TiempoAppConfig(AppConfig):
    name = 'tiempo.contrib.django_app'
    verbose_name = 'tiempo task running app'
    path = os.path.dirname(__file__)

    def ready(self):
        # TODO: I hate this.  I wish you had to do this manually.  - Justin
        if not getattr(settings, 'TIEMPO_MANUAL', False):  # This is the maximum about of boolean consideration I assert is preferable for this condition.  - Justin
            if not 'runtiempo' in sys.argv:  # This needs to be deprecated or refactored into a parsed argument.
                thread_init()
                auto_load_tasks()
