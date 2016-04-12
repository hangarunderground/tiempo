
from . import TIEMPO_REGISTRY, RECENT_KEY
from .task import Task, resolve_group_namespace
from .conn import REDIS
from .conf import INTERVAL, THREAD_CONFIG, RESULT_LIFESPAN, DEBUG
from .exceptions import ResponseError

from twisted.internet import threads, task
from dateutil.relativedelta import relativedelta
from cStringIO import StringIO
from logging import getLogger

import datetime
import sys
import chalk
import json
import pytz
import traceback


logger = getLogger(__name__)


def utc_now():
    return datetime.datetime.now(pytz.utc)


class CaptureStdOut(list):

    def __init__(self, *args, **kwargs):

        self.task = kwargs.pop('task')
        self.start_time = utc_now()

        super(CaptureStdOut, self).__init__(*args, **kwargs)

    def __enter__(self):
        if DEBUG:
            pass
            # return self
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        if DEBUG:
            # return
            pass

        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout

    def finished(self, timestamp=None):
        if DEBUG:
            pass
            # return

        self.timestamp = timestamp
        if not timestamp:
            self.timestamp = utc_now()

        task_key = '%s:%s' % (self.task.key, self.task.uid)
        expire_time = int(((self.timestamp + relativedelta(
            days=RESULT_LIFESPAN)) - self.timestamp).total_seconds())

        pipe = REDIS.pipeline()
        pipe.zadd(RECENT_KEY, self.start_time.strftime('%s'), task_key)
        pipe.set(self.task.uid, self.format_output())
        pipe.expire(self.task.uid, expire_time)
        pipe.execute()

    def format_output(self):

        return json.dumps(
            {
                'task': self.task.key,
                'uid': self.task.uid,
                'start_time': self.start_time.isoformat(),
                'end_time': self.timestamp.isoformat(),
                'duration': (self.timestamp - self.start_time).total_seconds(),
                'output': self
            }
        )


def get_task_keys(TASK_GROUPS):
    """
        creates a dictionary containing a mapping every combination of
        cron like keys with the corresponding amount of time
        until the next execution of such a task if it were to be executed
        now.


        ie:

        {'*.*.*': <1 minute from now>,}
        {'*.5.*': <1 minute from now>,}
        {'*.5.11': <24 hours from now>,}

    """

    time_keys = {}

    now = utc_now()

    # first any tasks that want to happen this minute.
    for tg in TASK_GROUPS:

        # every day, every hour, every minute
        time_keys['*.*.*'] = now + datetime.timedelta(minutes=1)

        # every day, every hour, this minute
        time_keys[now.strftime('*.*.%M')] = now + datetime.timedelta(hours=1)

        # every day, this hour, this minute
        time_keys[now.strftime('*.%H.%M')] = now + datetime.timedelta(days=1)

        # this day, this hour, this minute
        time_keys[now.strftime('%d.%H.%M')] = now + relativedelta(months=1)

        # this day, this hour, every minute
        time_keys[now.strftime('%d.%H.*')] = now + datetime.timedelta(minutes=1)

        # this day, every hour, every minute
        time_keys[now.strftime('%d.*.*')] = now + datetime.timedelta(minutes=1)

        # every day, this hour, every minute
        time_keys[now.strftime('*.%H.*')] = now + datetime.timedelta(minutes=1)

    # logger.debug(time_keys.keys())
    return time_keys


class ThreadManager(object):

    def __init__(self, number, thread_group_list):
        self.active_task = None
        self.task_groups = thread_group_list
        self.number = number

    def __repr__(self):
        return 'tiempo thread %d' % self.number

    def control(self):
        if self.active_task:
            msg = '%r currently busy with a task from %r'%(self, self.active_task)
            chalk.red(msg)
            logger.debug(msg)

        """
            First we check our task registry and check if there are any
            tasks that should be running right this second.

            If there are, we queue them.

            Next we execute queued tasks

        """

        now = utc_now()
        tomorrow = now + datetime.timedelta(days=1)

        time_tasks = get_task_keys(self.task_groups)

        _tasks = [
            t for t in TIEMPO_REGISTRY.values()
            if t.group in self.task_groups and t.periodic
        ]
        for _task in _tasks:
            stop_key = '%s:schedule:%s:stop' % (resolve_group_namespace(_task.group), _task.key)

            if hasattr(_task, 'force_interval'):
                expire_key = now + datetime.timedelta(
                    seconds=_task.force_interval
                )
            else:
                expire_key = time_tasks.get(_task.get_schedule())
            # the expire key is a datetime which signifies the NEXT time this
            # task would run if it was to be run right now.
            #
            # if there is no expire key it means that there are no tasks that
            # should run right now.

            if expire_key:
                # if we are here, it means we have a task that could run
                # right now if no other worker has already started it.
                try:

                    # create a key whose existence prevents this task
                    # from executing.  This will ensure that it only runs
                    # once across the whole network.

                    if REDIS.setnx(stop_key, 0):
                        logger.debug(
                            'running task %r because: %r',
                            _task, _task.get_schedule()
                        )
                        logger.debug('expire key: %r', expire_key)
                        logger.debug('now: %r', now)
                        logger.debug('stop key: %r', stop_key)
                        logger.debug(
                            'seconds: %r', (expire_key - now).total_seconds()
                        )
                        # the creation of the key was successful.
                        # this means that previous keys whose existence
                        # postponed execution for this task have expired.

                        # We will now set the expiration on this key to expire
                        # at the time of the next appropriate running of this
                        # task

                        REDIS.expire(
                            stop_key,
                            int(float((expire_key - now).total_seconds())) - 1
                        )

                        # queue it up
                        _task.soon()

                        logger.debug('next will be: %r', expire_key)

                except ResponseError as e:
                    print e
                except BaseException as e:
                    print e

        try:
            for g in self.task_groups:
                if not self.active_task:
                    msg = '%r checking for work in group %r' % (self, g)
                    chalk.blue(msg)
                    logger.debug(msg)
                    task = REDIS.lpop(resolve_group_namespace(g))
                    if task:
                        logger.debug(
                            'RUNNING TASK on thread %r: %s' % (self, task)
                        )
                        self.active_task = resolve_group_namespace(g)
                        return threads.deferToThread(run_task, task, self)

        except BaseException as e:
            chalk.red('%s got an error' % self)
            print traceback.format_exc()
            self.active_task = None

    def cleanup(self):
        pass
        # print 'thread %d cleaning up' % thread

    def start(self):
        task.LoopingCall(self.control).start(INTERVAL)


def run_task(task, thread):
    try:
        task = Task.rehydrate(task)
        chalk.yellow('%r STARTING: %s' % (thread, task.key))
        with CaptureStdOut(task=task) as output:
            try:
                task.run()
            except:
                print traceback.format_exc()
                task.finish(traceback.format_exc())

        output.finished()
        thread.active_task = None
    except AttributeError as e:
        thread.active_task = None
        print traceback.format_exc()


def thread_init():
    if len(THREAD_CONFIG):
        chalk.green('current time: %r' % utc_now())
        chalk.green(
            'Found %d thread(s) specified by THREAD_CONFIG' % len(THREAD_CONFIG)
        )

        for index, thread_group_list in enumerate(THREAD_CONFIG):
            tm = ThreadManager(index, thread_group_list)
            tm.start()
