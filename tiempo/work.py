from tiempo import RECENT_KEY

from dateutil.relativedelta import relativedelta
from hendrix.contrib.async.messaging import hxdispatcher

from tiempo.announce import Announcer
from tiempo.conf import RESULT_LIFESPAN, SCHEDULE_AHEAD_MINUTES, MAX_SCHEDULE_AHEAD_JOBS
from tiempo.utils import utc_now, namespace, task_time_keys


try:
    from django.utils.encoding import force_bytes
except ImportError:
    from tiempo.utils import force_bytes

try:
    from six.moves import cPickle as pickle
except ImportError:
    import pickle

from . import TIEMPO_REGISTRY

from .conn import REDIS

import inspect
import uuid
import importlib
import functools
import datetime
import json
import random
from twisted.logger import Logger
logger = Logger()

word_file = "/usr/share/dict/words"
WORDS = open(word_file).read().splitlines()


def announce_tasks_to_client():
    '''
    Push the list of tasks to the client.
    '''
    task_dict = {}

    for task in TIEMPO_REGISTRY.values():
        task_dict[task.key] = task.serialize_to_dict()
    hxdispatcher.send('all_tasks', {"tasks": task_dict})


class Job(object):
    '''
    A task running right now.
    '''

    def __init__(self, task, reconstitute_from=None, report_handler=None):
        self.task = task

        if reconstitute_from:
            self.uid = reconstitute_from['uid']
            self.code_word = reconstitute_from['codeWord']
            self.status = 'queued'
            self.enqueued = reconstitute_from['enqueued']
            self.args_to_function = reconstitute_from['args_to_function']
            self.kwargs_to_function = reconstitute_from['kwargs_to_function']
        else:
            self.uid = str(uuid.uuid4())
            self.code_word = task.code_word
            self.status = 'waiting'
            self.enqueued = False

        self.announcer = Announcer()

    def __str__(self):
        return "Job: %s / %s - (Task: %s, %s)" % (
            self.code_word,
            self.uid,
            self.task.key,
            self.task.uid
        )

    def serialize_to_dict(self):
        d = {'uid': self.uid,
             'codeWord': self.code_word,
             'key': self.task.key,
             'enqueued': self.enqueued,
             'status': self.status,
             'taskUid': self.task.uid,
             'group': self.task.group,  # TODO: Maybe do this client side.
             }
        return d

    def _freeze(self, *args, **kwargs):

        """
        creates a 'data' object which will be serialized and pushed into redis
        when this task is queued for execution.

        this data object should contain everything needed to reconstitute and
        execute the original function with args and kwargs in the context
        of a worker process
        """

        self.data = {
            'function_module_path': inspect.getmodule(self.task._get_function()).__name__,
            'function_name': self.task.func.__name__,
            'args_to_function': args,
            'kwargs_to_function': kwargs,
            'schedule': self.task.get_schedule(),
            'uid': self.uid,
            'codeWord': self.code_word,
        }
        self.frozen = True

        return self.data

    def _enqueue(self, queue_name):
        if not self.frozen:
            raise ValueError(
                'need to freeze this task before enqueuing'
            )

        # Announce that job is queued.
        self.enqueued = utc_now().isoformat()
        self.data['enqueued'] = self.enqueued  # TODO: Conventionalize serialization.
        self.status = "queued"
        self.announce('job_queue')

        job_string = self._encode(self.data)
        logger.info("Queueing %s: %s - %s" % (self.code_word, self.data["function_name"], self.data['uid']))
        REDIS.rpush(queue_name, job_string)

        return self.data['uid']

    def _enqueue_dependents(self):

        obj = REDIS.lpop(self.task.waitfor_key)
        if obj:
            awaiting_task = Job.rehydrate(obj)

            awaiting_task.soon(
                *getattr(awaiting_task, 'args_to_function', ()),
                **getattr(awaiting_task, 'kwargs_to_function', {})
            )

            self._enqueue_dependents()

    def _encode(cls, dictionary):
        return json.dumps(dictionary)

    @staticmethod
    def _decode(data):
        return json.loads(data)

    def soon(self, job_list=None, *args, **kwargs):
        """
        schedules this task to be run with the args and kwargs
        whenever a worker participating in this task's groups
        comes up as available
        """

        queue_name = job_list or self.task.group_key

        self._freeze(*args, **kwargs)
        self._enqueue(queue_name)
        return self

    def now(self, *args, **kwargs):
        """
        runs this task NOW with the args and kwargs
        """
        self.start()

        # TODO: Refactor into single run point for Job.
        self.task.args_to_function = args
        self.task.kwargs_to_function = kwargs
        result = self.task.run()
        self.finish()
        return result

    def announce(self, channel):
        hxdispatcher.send(channel, {'jobs':
                                        {self.uid: self.serialize_to_dict()}
                                    })

    def start(self, error=None):

        self.start_time = utc_now()

        logger.debug('Starting %s' % self.code_word)

        data = {
            'key': self.task.key,
            'uid':self.uid,
            'start': self.start_time.strftime('%y/%m/%d %I:%M%p'),
        }

        data['text'] =  """
%(key)s:
starting at %(start)s"""%data

        REDIS.set('tiempo_last_started_%s' % self.task.group_key, json.dumps(data))

        self.status = "running"
        self.announce('job_queue')

    def finish(self, error=None):
        try:
            logger.info('finished: %s (%s)' % (self.code_word, utc_now() - self.start_time))
        except AttributeError, e:
            # Somehow this job finished without ever being started.
            raise

        self._enqueue_dependents()

        now = utc_now()

        task_key = '%s:%s' % (self.task.key, self.uid)
        expire_time = int(((self.start_time + relativedelta(
            days=RESULT_LIFESPAN)) - self.start_time).total_seconds())

        pipe = REDIS.pipeline()
        pipe.zadd(RECENT_KEY, self.start_time.strftime('%s'), task_key)
        pipe.set(self.uid, self.serialize_to_dict())
        pipe.expire(self.uid, expire_time)
        pipe.execute()
        ### From old CaptureStdOut.finished()

        data = {
            'key': self.task.key,
            'uid': self.uid,
            'start': self.start_time.strftime('%y/%m/%d %I:%M%p'),
            'finished': now.strftime('%y/%m/%d %I:%M%p'),
            'elapsed': (now - self.start_time).seconds,
            'errors': 'with errors: %s' % error if error else ''
        }

        data['text'] =  """
            %(key)s:
            started at %(start)s
            finished in %(elapsed)s seconds
            %(errors)s""" % data

        REDIS.set('tiempo_last_finished_%s' % self.task.group_key, json.dumps(data))

        self.status = 'finished'
        self.announce('job_queue')

    @staticmethod
    def rehydrate(byte_string):

        d = Job._decode(byte_string)

        module = importlib.import_module(d['function_module_path'])
        t = getattr(module, d['function_name'])

        if not isinstance(t, Trabajo):
            # if the function that this task decorates is imported from
            # a different file path than where the decorating task is instantiated,
            # it will not be wrapped normally
            # so we wrap it.

            t = Trabajo(func=t)

        job = Job(reconstitute_from=d, task=t)
        return job


class Trabajo(object):
    '''
    espanol for task, and used interchangably with that word through Tiempo.

    This is the center of Tiempo's work model.

    A task is a callable and a set of scheduling logic that determines
    when and how to enqueue and run that callable.
    '''

    def __repr__(self):
        return self.key

    def __init__(self,
                 report_to=None,
                 announcer_name=None,
                 max_schedule_ahead=None,
                 *args, **kwargs):

        self.max_schedule_ahead = max_schedule_ahead or MAX_SCHEDULE_AHEAD_JOBS
        self.report_handler = report_to

        self.announcer_name = announcer_name

        self.day = None
        self.hour = None
        self.minute = None
        self.periodic = False
        self.force_interval = None
        self.current_job = None  # TODO: Push this knowledge down into the backend

        self.uid = str(uuid.uuid4())
        self.generate_code_word()

        self.key = ''
        self.function_name = None
        self.group = unicode(kwargs.get('priority', kwargs.get('group', '1')))  # TODO: refactor priority

        self.frozen = False
        # group and other attrs may be overridden here.
        for key, val in kwargs.items():
            setattr(self, key, val)

        if args and hasattr(args[0], '__call__'):
            self.__setup(args)

    def __call__(self, *args, **kwargs):

        # we only want this to happen if this is being called
        # as a decorator, otherwise all "calls" are performed as
        # special functions ie. "now" or "soon" etc.
        if args and hasattr(args[0], '__call__'):
            self.__setup(args)

        return self

    def __setup(self, args):
        self.func = args[0]
        self.cache = {}
        functools.update_wrapper(self, self.func)
        self.key = '%s.%s' % (
            inspect.getmodule(self.func).__name__, self.func.__name__
        )
        TIEMPO_REGISTRY[self.key] = self
        return self

    @property
    def group_key(self):
        return namespace(self.group)

    @property
    def waitfor_key(self):
        return namespace(self.uid)

    @property
    def stop_key(self):
        return '%s:schedule:%s:stop' % (namespace(self.group), self.key)

    def generate_code_word(self):
        word = random.choice(WORDS)
        self.code_word = unicode(word, encoding="UTF-8")
        return self.code_word

    def serialize_to_dict(self):
        next_run_time = self.datetime_of_subsequent_run()
        if next_run_time:
            next_run_time = next_run_time.isoformat()
        else:
            next_run_time = "Unscheduled."

        task_as_dict = {
            'codeWord': self.code_word,
            'path': self.key,
            'next_run_time': next_run_time,
            'uid': self.uid,
        }
        return task_as_dict

    def run(self, runner=None):
        """
        run right now
        """

        func = self._get_function()
        kwargs = getattr(self, 'kwargs_to_function', {})

        if self.announcer_name:
            kwargs[self.announcer_name] = runner.announcer

        result = func(
                *getattr(self, 'args_to_function', ()),
                **kwargs
                )
        return result

    def _thaw(self, data=None):
        """
            If this is called it is after a task has been instantiated by
            a worker process after being pulled as serialized data from redis
            and decoded.
            
            the for loop where the attrs are set from the data dict 
            will set this task to the same state as if it was 
            __init__ed as a decorator 
        """
        
        if not data and hasattr(self, 'data'):
            data = self.data

        if data:
            for key, val in data.items():
                setattr(self, key, val)

    def _get_function(self):
        if hasattr(self, 'func'):
            return self.func

        if not self.function_name:
            self._thaw()

        if hasattr(self, 'function_module_path'):

            module = importlib.import_module(self.function_module_path)
            obj = getattr(module, self.function_name)

            if hasattr(obj, 'func'):
                return obj.func
            return obj
        else:
            print "could not find function", self.func

    def is_planned(self):
        '''
        TODO: Account for dependent tasks and tasks that have recently
        had their 'soon()' method called.
        '''
        if not self.force_interval and not self.periodic:
            return False
        else:
            return True

    def get_schedule(self):
        if self.periodic:
            sched = [
                '*',
                '*',
                '*'
            ]
            for i, inc in enumerate(['day', 'hour', 'minute']):
                attr = getattr(self, inc, None)
                if attr is not None:
                    if attr != '*':
                        attr = '%02d' % int(attr)
                    sched[i] = attr

            return '.'.join(sched)

    def next_expiration_dt(self):
        '''
        The next future datetime at which this trabajo's waiting period will expire.
        '''
        if self.force_interval:
            expiration_dt = utc_now() + datetime.timedelta(
                seconds=self.force_interval
            )
        else:
            run_times = task_time_keys()
            schedule = self.get_schedule()
            expiration_dt = run_times.get(self.get_schedule())

        return expiration_dt

    def runs_every_minute(self):
        '''
        A convenience method to determine whether a task
        runs once per minute on schedule.
        '''
        return self.periodic and not(self.force_interval or self.minute or self.hour or self.day)

    def delta_until_run_time(self, dt=None):
        '''
        Takes a datetime, which defaults to utc_now().

        If this task is currently planned, returns a relativedelta from dt when it is eligible to be queued.

        (e.g., if it's 3:51, and this Trabajo runs every hour at 20 after the hour, then this function will return relativedelta(hours=+1, minute=20), the duration from now until 4:20)

        If not planned, returns None.

        TODO: If task is currently enqueued, return some kind of ENQUEUED object.
        '''
        dt = dt or utc_now()

        if self.is_planned():

            if self.force_interval:
                seconds = self.force_interval
                last_run = REDIS.get(namespace("last_run:%s" % self.uid))
                if not last_run:  # If we've never run before...
                    return datetime.timedelta(seconds=seconds)
                else:
                    raise RuntimeError("Not implemented.")

            # If this task runs every minute, we know that we need to simply add a minute to the dt to get the next runtime.
            if self.runs_every_minute():
                return relativedelta(minutes=+1)

            r = relativedelta()

            next_hour = False
            next_day = False

            if self.minute:
                r += relativedelta(minute=self.minute)

                # Read as "If the current minute is already past the minute of run time, we do this next hour."
                next_hour = dt.minute >= self.minute

            if self.hour:
                r += relativedelta(hour=self.hour)

                # Same as 'next hour' above, but for day.
                if dt.hour >= self.hour:
                    next_day = True
            elif next_hour:
                r += relativedelta(hours=+1)

            if self.day:
                r += relativedelta(day=self.day)
                if dt.day >= self.day:
                    r += relativedelta(months=+1)
            elif next_day:
                r += relativedelta(days=+1)

            return r
        else:
            return None

    def datetime_of_subsequent_run(self, dt=None):
        """
        Takes a datetime, which defaults to utc_now().

        If this task is currently planned, returns the first time after dt when this task is eligible to be run.

        Otherwise, returns None.
        """
        dt = dt or utc_now()
        r = self.delta_until_run_time(dt)
        if r is not None:
            return dt + r

    def check_schedule(self, window_begin=None, window_end=None):
        '''
        Takes a datetime, window_begin, which defaults to utc_now() without microseconds.
        Takes a datetime, window_end, which default to one hour after dt.

        Checks to see if this task can be enqueued at 1 or more times
        between window_begin and window_end.

        Returns a list of datetime objects at which scheduling this task is appropriate.
        '''
        window_begin = window_begin or utc_now().replace(microsecond=0)
        window_end = window_end or window_begin + datetime.timedelta(minutes=SCHEDULE_AHEAD_MINUTES)

        run_times = []

        while True:
            if len(run_times) >= self.max_schedule_ahead:
                break

            dt_of_next_run = self.datetime_of_subsequent_run(window_begin)

            if dt_of_next_run:  # TODO: When is this False?
                if dt_of_next_run < window_end:

                    # This dt checks out.  Add it.
                    run_times.append(dt_of_next_run)

                    # To find a subsequent run, start searching at this time.
                    window_begin = dt_of_next_run

                else:
                    break  # This dt is after the window_end.
            else:
                break  # There is no qualifying dt in this timeframe.  TODO: Test this.
        return run_times

    def currently_scheduled_keys(self):
        '''
        Returns the backend keys for currently scheduled future runs.
        '''
        pattern = namespace('scheduled:%s:*' % self.key)
        keys = REDIS.keys(pattern)
        return keys

    def currently_scheduled_in_seconds(self):
        '''
        Returns a list of ints or longs, with each item being a number of seconds in the future at which this task will run.
        '''
        pipe = REDIS.pipeline()
        for key in self.currently_scheduled_keys():
            pipe.ttl(key)
        seconds_list = pipe.execute()
        seconds_list.sort()
        return seconds_list

    def just_spawn_job(self, default_report_handler=None):
        # If this task has a report handler, use it.  Otherwise, use a default if one is passed.
        report_handler = self.report_handler or default_report_handler

        # TODO: Implement report handler

        job = Job(task=self)
        return job

    def spawn_job_and_run_soon(self,
                  job_list=None,
                  default_report_handler=None,
                  *args,
                  **kwargs):
        '''
        Create a Job object for this task and push it to the queue with args and kwargs.
        '''
        job = self.just_spawn_job(default_report_handler)
        job.soon(job_list=namespace(job_list), *args, **kwargs)

        # Now we generate a new code word for next time.
        self.generate_code_word()

        logger.info("Spawned job %s (%s) for %s (%s).  Code word next time: %s" % (
                        job.code_word,
                        job.uid,
                        self.key,
                        self.uid,
                        self.code_word
                        )
                    )

        return job

    def spawn_job_and_run_now(self, *args, **kwargs):
        job = self.just_spawn_job()
        return job.now(*args, **kwargs)

    def soon(self, tiempo_wait_for=None,
             *args, **kwargs):
        '''
        Just like spawn_job_and_run_roon(), but returns self instead of the job.

        Also takes argument "tiempo_wait_for" for backward compat.
        '''

        # If we are told to wait for another task, we'll put this in the appropriately named queue.
        self.spawn_job_and_run_soon(job_list=tiempo_wait_for, *args, **kwargs)
        return self

    def now(self, *args, **kwargs):
        """
        runs this task NOW with the args and kwargs
        """
        result = self.spawn_job_and_run_now(*args, **kwargs)
        return result


task = Trabajo  # For compatibility as a drop-in Celery replacement.
