
try:
    from django.utils.encoding import force_bytes
except ImportError:
    from .utils import force_bytes

try:
    from six.moves import cPickle as pickle
except ImportError:
    import pickle

from . import TIEMPO_REGISTRY
from . import REDIS_GROUP_NAMESPACE as group_ns
from .conn import REDIS

from logging import getLogger

import inspect
import uuid
import base64
import importlib
import functools
import datetime
import traceback
import json


logger = getLogger(__name__)


def resolve_group_namespace(group_name):
    return '%s:%s'%(group_ns, group_name)

class TaskBase(object):

    @property
    def html(self):
        return '<task>%s</task>' % self.uid

    @classmethod
    def _encode(cls, dictionary):
        "Returns the given session dictionary pickled and encoded as a string."
        try:
            pickled = pickle.dumps(dictionary, pickle.HIGHEST_PROTOCOL)
        except pickle.PicklingError as E:
            msg = "PICKLING ERROR.  You have some complex data in the arguments to %r that cannot be pickled"%self
            print msg
            raise E(msg)
        return base64.b64encode(pickled).decode('ascii')

    @staticmethod
    def _decode(data):

        encoded_data = base64.b64decode(force_bytes(data))
        try:
            # could produce ValueError if there is no ':'
            pickled = encoded_data
            dec = pickle.loads(pickled)
            # print 'pickle:', dec
            return dec

        except Exception:
            raise
            # ValueError, SuspiciousOperation, unpickling exceptions. If any of
            # these happen, just return an empty dictionary (an empty session).
            return {}

    @staticmethod
    def rehydrate(base_64):

        d = Task._decode(base_64)
            
        # we now have a dictionary like this:
        #    {
        #    'function_module_path': "a.path.to.a.function",
        #    'function_name': "the function name",
        #    'args_to_function': (some, args),
        #    'kwargs_to_function': {"keyword_arg_count": 1},
        #    'schedule': "*.*.*",
        #    'uid': "1234-12345678-12345678-1234",
        #    }
        
        module = importlib.import_module(d['function_module_path'])
        T = getattr(module, d['function_name'])
        
        if not isinstance(T, Task):
            # if the function that this task decorates is imported from
            # a different file path than where the decorating task is instantiated,
            # it will not be wrapped normally
            # so we wrap it.
            
            T = Task(T)
        
        T.data = d
        T._thaw()
        return T


class Task(TaskBase):

    def __repr__(self):
        return self.key

    def __init__(self, *args, **kwargs):

        self.day = None
        self.hour = None
        self.minute = None
        self.periodic = False

        self.uid = str(uuid.uuid1())

        self.key = self.uid
        self.function_name = None
        self.group = unicode(kwargs.get('priority', kwargs.get('group','1')))

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
        return resolve_group_namespace(self.group)

    @property
    def waitfor_key(self):
        return resolve_group_namespace(self.uid)

    def _freeze(self, *args, **kwargs):
        
        """
            creates a 'data' object which will be serialized and pushed into redis
            when this task is queued for execution.
            
            this data object should contain everything needed to reconstitute and 
            execute the original function with args and kwargs in the context
            of a worker process
        """
    
        # make a fresh uid specific to this instance that will persist
        # through getting saved to the queue        
        self.uid = str(uuid.uuid1())

        self.data = {
            'function_module_path': inspect.getmodule(self._get_function()).__name__,
            'function_name': self.func.__name__,
            'args_to_function': args,
            'kwargs_to_function': kwargs,
            'schedule': self.get_schedule(),
            'uid': self.uid,
        }
        self.frozen = True

        return self.data

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

    def _enqueue(self, queue_name):
        if not self.frozen:
            raise ValueError(
                'need to freeze this task before enqueuing'
            )

        print "enqueueing", self
        d = self._encode(self.data)

        REDIS.rpush(queue_name, d)
        return self.data['uid']

    def _enqueue_dependents(self):

        obj = REDIS.lpop(self.waitfor_key)
        if obj:
            awaiting_task = Task.rehydrate(obj)
            #queue it
            print 'enqueing:', awaiting_task,'uid',awaiting_task.uid, 'with waitfor:', self.waitfor_key

            awaiting_task.soon(
                *getattr(awaiting_task, 'args_to_function', ()),
                **getattr(awaiting_task, 'kwargs_to_function', {})
            )

            self._enqueue_dependents()

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

    def run(self):
        """
            runs this task right now
        """
        self.start()

        try:
            func = self._get_function()
            result = func(
                *getattr(self, 'args_to_function', ()),
                **getattr(self, 'kwargs_to_function', {})
            )
            self.finish()

            return result

        except Exception as e:
            errtext = traceback.format_exc()
            self.finish(error=errtext)

    def soon(self, *args, **kwargs):
        """
            schedules this task to be run with the args and kwargs
            whenever a worker participating in this task's groups
            comes up as available

        """
        logger.debug('scheduling task %r for next available execution', self)

        queue_name = kwargs.pop('tiempo_wait_for', None)

        if queue_name:
            queue_name = resolve_group_namespace(queue_name)
        else:
            queue_name = self.group_key

        self._freeze(*args, **kwargs)
        self._enqueue(queue_name)
        return self

    def now(self, *args, **kwargs):
        """
            runs this task NOW with the args and kwargs
        """
        self._freeze(*args, **kwargs)
        self._thaw()
        return self.run()

    def finish(self, error=None):
        #print 'finished:', self.uid
        self._enqueue_dependents()

        now = datetime.datetime.now()
        data = {
            'key': self.key,
            'uid':self.uid,
            'start': self.start_time.strftime('%y/%m/%d %I:%M%p'),
            'finished': now.strftime('%y/%m/%d %I:%M%p'),
            'elapsed':(now-self.start_time).seconds,
            'errors': 'with errors: %s'%error if error else ''
        }

        data['text'] =  """
%(key)s:
started at %(start)s
finished in %(elapsed)s seconds
%(errors)s"""%data

        REDIS.set('tiempo_last_finished_%s'%self.group_key, json.dumps(data))

    def start(self, error=None):

        self.start_time = datetime.datetime.now()
        now = datetime.datetime.now()

        data = {
            'key': self.key,
            'uid':self.uid,
            'start': self.start_time.strftime('%y/%m/%d %I:%M%p'),
        }

        data['text'] =  """
%(key)s:
starting at %(start)s"""%data

        REDIS.set('tiempo_last_started_%s'%self.group_key, json.dumps(data))

task = Task
