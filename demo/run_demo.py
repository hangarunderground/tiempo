import os, sys

from hendrix.deploy.base import HendrixDeploy
from django.conf import settings
from hendrix.facilities.resources import NamedResource
from twisted.internet.protocol import Factory
from txsockjs.factory import SockJSResource

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# begin chdir armor
sys.path[:] = map(os.path.abspath, sys.path)
# end chdir armor

tiempo_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, tiempo_path)

from tiempo.resource import TiempoMessageProtocol

from twisted.logger import (
    ILogObserver, LogLevel, globalLogPublisher, formatEvent, FilteringLogObserver, LogLevelFilterPredicate
)
from zope.interface import provider

@provider(ILogObserver)
def simpleObserver(event):
    print(formatEvent(event))

tiempo_demo_observer = FilteringLogObserver(simpleObserver, [LogLevelFilterPredicate(defaultLogLevel=LogLevel.info)])

globalLogPublisher.addObserver(tiempo_demo_observer)


settings.configure(
    MIDDLEWARE_CLASSES=[],
    ROOT_URLCONF='tiempo_web.urls',
    DEBUG=True,

    INSTALLED_APPS=[
        'tiempo',
        'tiempo.contrib.django_app',
        'tiempo_web',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.staticfiles',
        ],
    SECRET_KEY="LLAMAS",

    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    },
    STATIC_URL='/static/',
    TIEMPO_THREAD_CONFIG=[('1', '2', '3'), ('1',)]
)


from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

deployer = HendrixDeploy(options={'wsgi': application,
                                  'http_port': 4050,
                                  'loud': True,
                                  }
                         )

TiempoMessageResource = NamedResource('tiempo_communication')
TiempoMessageResource.putChild(
    'messages',
    SockJSResource(Factory.forProtocol(TiempoMessageProtocol))
)

deployer.resources.append(TiempoMessageResource)

deployer.run()
