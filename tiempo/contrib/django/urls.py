from django.conf.urls import patterns, url

urlpatterns = patterns(
    'tiempo.contrib.django.views',
    url(r'^recent/$', 'recent_tasks', name='recent_tasks'),
    url(r'^results/(?P<key>.+)', 'results', name='task_results')
)
