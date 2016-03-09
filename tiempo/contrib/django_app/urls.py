from django.conf.urls import patterns, url

urlpatterns = patterns(
    'tiempo.contrib.django_app.views',
    url(r'^$', 'dashboard', name='tiempo_dashboard'),
    url(r'^all_tasks/$', 'all_tasks', name='all_tiempo_tasks'),
    url(r'^recent/$', 'recent_tasks', name='recent_tasks'),
    url(r'^results/(?P<key>.+)', 'results', name='task_results')
)
