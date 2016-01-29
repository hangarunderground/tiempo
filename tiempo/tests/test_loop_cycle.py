from tiempo import tiempo_loop, TIEMPO_REGISTRY
import string
import random
import time
import datetime
from collections import deque

from twisted.internet import task
from twisted.trial.unittest import TestCase

from six.moves.queue import Queue
from tiempo.conn import subscribe_to_backend_notifications, REDIS, check_backend
from tiempo.tests.sample_tasks import some_callable
from tiempo.tiempo_loop import schedule_tasks_for_queueing, glean_events_from_backend, cycle
from tiempo.work import Trabajo
from tiempo.runner import Runner
from tiempo.insight import completed_jobs
from tiempo.utils import utc_now
from tiempo.utils.premade_decorators import minutely_task

q = Queue()
random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))


def unblocker():
    q.put(random_string)


class WholeCycleTests(TestCase):

    def setup(self):
        TIEMPO_REGISTRY.clear()
        REDIS.flushall()
        clock = task.Clock()
        self.looper = task.LoopingCall(cycle)
        self.looper.start(1)
        runner0 = Runner(0, [1])
        runner1 = Runner(1, [1])
        runner2 = Runner(2, [2])
        minutely = Trabajo(priority=1, periodic=True, second=30)(some_callable)
        for x in range(0, 10000):
            clock.advance(1)

    def teardown(self):
        self.looper.stop()
        REDIS.flushall()

    def test_glean_returns_event_queue(self):
        events = glean_events_from_backend()
        self.assertIsInstance(events, deque)

    def test_whole_cycle(self):
        self.fail()

class ScheduleExpiryTests(TestCase):
    '''
    When scheduled items expire from redis, it's time to run them.
    '''

    def setUp(self):
        TIEMPO_REGISTRY.clear()
        REDIS.flushall()

    def test_that_expiry_triggers_scheduling(self):
        subscribe_to_backend_notifications()
        decorated = Trabajo(force_interval=1)(some_callable) # Puts the task in TIEMPO_REGISTRY
        schedule_tasks_for_queueing()
        # TODO: Is there a better way to wait for REDIS expiry notifications?
        subscribe_events = glean_events_from_backend()
        time.sleep(2)
        other_events = glean_events_from_backend()
        tiempo_loop.queue_scheduled_tasks(other_events)

    def test_consecutive_scheduling_force_interval(self):

        int_const = 1

        # create a task with a forced interval of 1 second.
        forced_interval = Trabajo(force_interval=int_const)(some_callable)

        queued = forced_interval.currently_scheduled_keys()
        self.assertEqual(len(queued), 0)

        schedule_tasks_for_queueing()
        queued = forced_interval.currently_scheduled_keys()

        # extract the list of unix timestamps from the redis scheduled keys
        orig_times = [int(key.split(':')[-1]) for key in queued]
        orig_times.sort()

        self.assertEqual(len(queued), 100)

        # wait 1 second so... any time values that would be generated
        # on subsequent scheduling iterations would be different
        time.sleep(int_const)

        # schedule again
        schedule_tasks_for_queueing()
        queued = forced_interval.currently_scheduled_keys()

        # extract the list of unix timestamps from the redis scheduled keys
        times = [int(key.split(':')[-1]) for key in queued]
        times.sort()

        # there should be no new tasks scheduled
        self.assertEqual(len(queued), 100)

        # the keys should NOT still be the same because we have waited for a
        # scheduled key to expire and re-run the `schedule_tasks_for_queueing`
        # which would schedule a more recent scheduled key for this
        # force_interval task
        self.assertNotEqual(orig_times, times)
        self.assertEqual(times[0] - orig_times[0], int_const)

        intervals = list(
            set([new - old for new, old in zip(times, orig_times)])
        )
        # assert that all of the intervals are the same i.e. the force_interval
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0], int_const)

    def test_consecutive_scheduling_periodic(self):
        window_begin = utc_now()
        window_end = window_begin + datetime.timedelta(hours=3, minutes=20)

        # this task should run once per hour so if we have a window of 3 hours,
        # it should get scheduled to run 3x.

        periodic = Trabajo(
            periodic=True,
            minute=(window_begin.minute+3)%60
        )(some_callable)

        queued = periodic.currently_scheduled_keys()
        self.assertEqual(len(queued), 0)

        schedule_tasks_for_queueing()
        queued = periodic.currently_scheduled_keys()
        first_key = queued[0]
        last_key = queued[-1]

        self.assertEqual(len(periodic.currently_scheduled_keys()), 3)

        # wait 2 seconds so... any time values that would be generated
        # on subsequent scheduling iterations would be different by 2 seconds
        time.sleep(2)

        # schedule again
        schedule_tasks_for_queueing()
        # there should be no new tasks scheduled
        self.assertEqual(len(periodic.currently_scheduled_keys()), 3)

        # the keys should still be the same
        self.assertEqual(queued[0], first_key)
        self.assertEqual(queued[-1], last_key)
