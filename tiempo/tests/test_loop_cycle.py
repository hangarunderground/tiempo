from tiempo import tiempo_loop, TIEMPO_REGISTRY
import string
import random
import time

from twisted.trial.unittest import TestCase

from six.moves.queue import Queue
from tiempo.conn import subscribe_to_backend_notifications, REDIS
from tiempo.tests.sample_tasks import some_callable
from tiempo.tiempo_loop import schedule_tasks_for_queueing, glean_events_from_backend
from tiempo.work import Trabajo


q = Queue()
random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))


def unblocker():
    q.put(random_string)


# class WholeCycleTests(TestCase):
#
#     def test_whole_cycle(self):
#         tiempo_loop.cycle()
#         self.fail()

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