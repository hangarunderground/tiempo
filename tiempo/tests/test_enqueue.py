import datetime
from twisted.trial.unittest import TestCase
from tiempo.tests.sample_tasks import some_callable
from tiempo.utils import utc_now
from tiempo.utils.premade_decorators import hourly_task, daily_task


class TaskQueueTests(TestCase):

    def test_task_is_not_added_to_queue_if_not_time_yet(self):
        task = daily_task(some_callable)
        window_begin = datetime.datetime(2006, 4, 26, 12, 30, 45)
        window_end = window_begin + datetime.timedelta(hours=3)

        # Since our task runs at the first hour, we expect it not to be scheduled in this window.
        queued = task.check_schedule(window_begin, window_end)
        self.assertEqual(queued, [])

    def test_hourly_task_is_scheduled_three_times_in_three_hours(self):
        task = hourly_task(some_callable)

        window_begin = utc_now()
        window_end = window_begin + datetime.timedelta(hours=3)

        queued = task.check_schedule(window_begin, window_end)
        self.assertEqual(len(queued), 3)