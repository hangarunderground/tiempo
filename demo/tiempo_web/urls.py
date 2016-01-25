from django.conf.urls import include, url

from tiempo.contrib.django_app.views import TiempoKiosk, TiempoHistory

urlpatterns = [
    url(r'^tiempo/', include('tiempo.contrib.django_app.urls')),
    url(r'^tiempo_kiosk', TiempoKiosk.as_view()),
    url(r'^history', TiempoHistory.as_view()),
]