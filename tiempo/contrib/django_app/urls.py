from django.conf.urls import patterns, url, include

from tiempo.contrib.django_app.api.urls import tiempo_api_router
from tiempo.contrib.django_app.views import TiempoKiosk

urlpatterns = patterns(
    'tiempo.contrib.django_app.views',
    url(r'^$', 'dashboard', name='tiempo_dashboard'),
    url(r'^kiosk/$', TiempoKiosk.as_view(), name="Tiempo Live Kiosk"),
    url(r'^history/$', TiempoKiosk.as_view(), name="Tiempo Task History"),
    url(r'^recent/$', 'recent_tasks', name='recent_tasks'),
    url(r'^results/(?P<key>.+)', 'results', name='task_results'),
    url(r'^api/v1/', include(tiempo_api_router.urls)),
)