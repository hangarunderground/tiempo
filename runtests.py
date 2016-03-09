#! python

import os, sys
import tiempo
tiempo.LEAVE_DJANGO_UNSET = True

from tiempo import conf
from twisted.scripts.trial import run as run_tests
conf.REDIS_QUEUE_DB = conf.REDIS_TEST_DB

# begin chdir armor
sys.path[:] = map(os.path.abspath, sys.path)
# end chdir armor

sys.path.insert(0, os.path.abspath(os.getcwd()))
sys.argv.append("tiempo/tests")
sys.argv.append("tiempo/contrib/django_app/tests.py")

####
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def run_django_settings():
    from django.conf import settings
    settings.configure(
        MIDDLEWARE_CLASSES=[],
        ROOT_URLCONF='tiempo.contrib.django_app.urls',
        TIEMPO_MANUAL=True,
        INSTALLED_APPS=[
            'tiempo.contrib.django_app',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            ],
        SECRET_KEY="LLAMAS",

        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
            }
        },
        ALLOWED_HOSTS="*",
        DEBUG=True,
    )
    import django
    django.setup()

run_django_settings()
run_tests()

