
from datetime import datetime
from tiempo.execution import REDIS, RECENT_KEY
from tiempo.task import resolve_group_namespace as rgn, Task
from tiempo.task import task
from tiempo import conf as tiemposettings
from tiempo import TIEMPO_REGISTRY

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse

import pytz
import json
import dateutil.parser

utc = pytz.timezone('UTC')
local = pytz.timezone("America/New_York")



def dashboard(request):

    threads = tiemposettings.THREAD_CONFIG

    queue_length = [
        {
        'name': t, 
        'length': REDIS.llen(rgn(t)),
        'started': json.loads(REDIS.get('tiempo_last_started_%s'%rgn(t))) if REDIS.get('tiempo_last_started_%s'%rgn(t)) else {},
        'finished': json.loads(REDIS.get('tiempo_last_finished_%s'%rgn(t))) if REDIS.get('tiempo_last_finished_%s'%rgn(t)) else {},
        'next': task._decode(REDIS.lindex(rgn(t), 0)) if REDIS.lindex(rgn(t), 0) else ''
        }
        for t in sorted(list(set([p for g in threads for p in g])))
    ]

    response = render(request, 'tiempo/dashboard.html', {
        'queue_info': queue_length,
        'title': 'Tiempo Dashboard'
    })
    return response


def all_tasks(request):
    tasks = TIEMPO_REGISTRY

    response = render(request, 'tiempo/all_tasks.html', {
        'tasks': tasks
    })
    return response


@login_required
def recent_tasks(request):
    start = int(request.GET.get('offset', 0))
    end = start + int(request.GET.get('limit', 1000))

    recent = REDIS.zrevrange(RECENT_KEY, start, end, withscores=True)
    # recent.reverse()

    out = [
        {
            'datetime': datetime.fromtimestamp(
                timestamp).replace(tzinfo=utc).astimezone(local),
            'taskname': task.split(':')[0],
            'uid': task.split(':')[-1]
        } for task, timestamp in recent
    ]

    response = render(request, 'tiempo/recent.html', {
        'tasks': out,
        'title': 'Tiempo Recent'
    })
    return response


@login_required
def results(requests, key):

    # {u'task': u'apps.brand.tasks.update_youtube_member_channels_nightly',
    # u'uid': u'4856ab75-5964-11e4-9d8b-5cf938a858da',
    # u'start_time': u'2014-10-21T20:53:32.582777+00:00', u'end_time':
    # u'2014-10-21T20:53:32.602500+00:00', u'duration': 0.019723, u'output':
    # [u'update_youtube_member_channels_nightly',
    #  u'found 0 CampaignCreators needing updates']}
    task = json.loads(REDIS.get(key))
    content = {}

    for key, val in task.items():
        if 'time' in key:
            content[key] = dateutil.parser.parse(val).strftime('%a %H:%M:%S')
        elif key == 'output':
            content[key] = '<br>'.join(val)
        else:
            content[key] = val

    return HttpResponse(
        json.dumps(content),
        content_type='application/json',
        status=200
    )
