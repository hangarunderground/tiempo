import os
import sys

from tiempo.execution import thread_init
from .utils.loader import auto_load_tasks
from django.apps import AppConfig, apps

print "loaded tiempo"

class TiempoAppConfig(AppConfig):
    name = 'tiempo.contrib.django'
    verbose_name = 'tiempo task running app'
    path = os.path.dirname(__file__)

    def ready(self):
        if not 'runtiempo' in sys.argv:
            print 'initing tasks'
            thread_init(executable_path="%s/manage.py"%os.getcwd(), args=['runtiempo'])
            auto_load_tasks()
