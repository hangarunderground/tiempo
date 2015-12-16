from django.conf.urls import patterns, url
from tiempo.contrib.django.views import TiempoKiosk

urlpatterns = patterns(
    'tiempo.contrib.django.views',
    url(r'^$', 'dashboard', name='tiempo_dashboard'),
    url(r'^kiosk/$', TiempoKiosk.as_view(), name="Tiempo Live Kiosk"),
    url(r'^history/$', TiempoKiosk.as_view(), name="Tiempo Task History"),
    url(r'^recent/$', 'recent_tasks', name='recent_tasks'),
    url(r'^results/(?P<key>.+)', 'results', name='task_results')
)
