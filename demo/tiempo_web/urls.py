from django.conf.urls import include, url, patterns

from tiempo.contrib.django_app.api.urls import tiempo_api_router
from tiempo.contrib.django_app.views import TiempoKiosk

urlpatterns = patterns('',
    url(r'^tiempo/api/v1/', include(tiempo_api_router.urls)),
    url(r'^tiempo_kiosk', TiempoKiosk.as_view()),
    # url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
)