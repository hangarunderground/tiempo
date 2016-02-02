import datetime
from collections import deque
from twisted.trial.unittest import TestCase
from tiempo import TIEMPO_REGISTRY
from tiempo.tests.sample_tasks import some_callable
from tiempo.conn import REDIS
from tiempo.work import Trabajo
from tiempo.queueing import queue_expired_tasks, queue_jobs
from tiempo.utils import utc_now
from tiempo.utils.premade_decorators import hourly_task, daily_task


class TaskQueueTests(TestCase):

    def test_task_is_not_added_to_queue_if_not_time_yet(self):
        # this runs at 1:00am
        task = daily_task(some_callable)

        window_begin = datetime.datetime(2006, 4, 26, 12, 30, 45)
        window_end = window_begin + datetime.timedelta(hours=3)

        # Since our task runs at the first hour, we expect it not to be scheduled in this window.
        queued = task.check_schedule(window_begin, window_end)
        self.assertEqual(queued, [])

    def test_hourly_task_is_scheduled_three_times_in_three_hours(self):
        # this runs at :30 minutes past the hour
        task = hourly_task(some_callable)

        window_begin = utc_now()
        window_end = window_begin + datetime.timedelta(hours=3)

        queued = task.check_schedule(window_begin, window_end)
        self.assertEqual(len(queued), 3)


class QueueTests(TestCase):

    event_list = deque([
        {'pattern': '__keyevent@13__:expired', 'type': 'pmessage', 'data': 'tiempogroup:scheduled:tiempo.tests.sample_tasks.some_callable:1454345452', 'channel': '__keyevent@13__:expired'},
        {'type': 'psubscribe', 'channel': '__keyspace@13__:results*', 'pattern': None, 'data': 2L},
        {'type': 'pmessage', 'channel': '__keyspace@13__:results:whatever', 'pattern': '__keyspace@13__:results*', 'data': 'set'}])

    def setup(self):
        REDIS.flushall()

    def test_queue_expired_tasks(self):
        run_now_dict = queue_expired_tasks(self.event_list)
        self.assertIsInstance(run_now_dict, dict)

    def test_queue_jobs_raises_error(self):
        TIEMPO_REGISTRY.clear()
        run_now_dict = queue_expired_tasks(self.event_list)
        self.assertRaises(KeyError, queue_jobs, run_now_dict)

    def test_calling_task_creates_job(self):
        TIEMPO_REGISTRY.clear()
        run_now_dict = queue_expired_tasks(self.event_list)
        decorated = Trabajo()(some_callable)
        queued_jobs = queue_jobs(run_now_dict)
        self.assertIsInstance(queued_jobs, dict)
