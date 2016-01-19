import json
import uuid
from tiempo import TIEMPO_REGISTRY, tiempo_loop
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from twisted.trial.unittest import TestCase

from sample_tasks import some_callable
from tiempo.conn import REDIS
from tiempo.utils import namespace, utc_now
from tiempo.work import Trabajo
import unittest
from tiempo.utils.premade_decorators import daily_task, hourly_task, monthly_task, minutely_task, unplanned_task


class ScheduleBackendTests(TestCase):

    def setUp(self):
        TIEMPO_REGISTRY.clear()
        REDIS.flushall()

    def test_force_interval_gets_job_scheduled_on_first_cycle(self):
        schedule_ahead = 50
        decorated = Trabajo(force_interval=3, max_schedule_ahead=schedule_ahead)(some_callable)

        # Now do the scheduling.
        tiempo_loop.schedule_tasks_for_queueing()

        interval_list = decorated.currently_scheduled_in_seconds()

        # At only three seconds, we expect this to be scheduled to the max.
        self.assertEqual(len(interval_list), schedule_ahead)

        try:
            last_value = interval_list.pop(0)
        except IndexError:
            self.fail("We got an empty list of the current schedule.  That ain't right.")

        while interval_list:
            this_value = interval_list.pop(0)
            difference = this_value-last_value
            self.assertEqual(difference, 3L)
            last_value = this_value


class TaskScheduleTests(TestCase):

    def setUp(self):
        TIEMPO_REGISTRY.clear()
        REDIS.flushall()
        self.check_from_time = datetime(2006, 4, 26, 12, 30, 45)

    def test_scheduled_tasks_have_proper_schedule(self):
        minutely = minutely_task(some_callable)
        hourly = hourly_task(some_callable)
        daily = daily_task(some_callable)
        monthly = monthly_task(some_callable)

        self.assertEqual(minutely.get_schedule(), '*.*.*')
        self.assertEqual(hourly.get_schedule(), '*.*.30')
        self.assertEqual(daily.get_schedule(), '*.01.*')
        self.assertEqual(monthly.get_schedule(), '04.14.17')

    @unittest.skip("Pending new logic.")
    def test_minutely_tasks_expire_in_60_seconds(self):
        self.fail()
        # Here's how this used to work, when next_expiration_dt() was a thing:
        minutely_task = Trabajo(priority=1, periodic=True)
        minutely = minutely_task(some_callable)
        now = utc_now()

        minutely_expiration = minutely.next_expiration_dt()
        minutely_delta = minutely_expiration - now
        self.assertEqual(minutely_delta.seconds, 60)

    def test_now_with_args_runs_with_args(self):
        unscheduled_task = unplanned_task(some_callable)
        random_arg = uuid.uuid4()
        result = unscheduled_task.now(random_arg)

        # Our callable simply returns a tuple of args and kwargs passed to it, so we'll have gotten the uuid back.
        args, kwargs = result
        self.assertEqual(args[0], random_arg)

    def test_dependent_task_gets_scheduled_by_soon(self):
        this_may_as_well_be_a_uid = "a large farva"

        dependent_task = unplanned_task(some_callable)

        dependent_task.soon(tiempo_wait_for=this_may_as_well_be_a_uid, run_with="something_very_unique_and_strange")
        task_dict_json = REDIS.lpop(namespace(this_may_as_well_be_a_uid))
        task_dict = json.loads(task_dict_json)
        self.assertEqual(task_dict['kwargs_to_function']['run_with'], "something_very_unique_and_strange")

    def test_dependent_task_is_queued_after_trigger_task(self):
        unscheduled_task = unplanned_task(some_callable)

        dependent_task = unplanned_task(some_callable)

        # Mark this task as dependent on unscheduled_task.
        dependent_task.soon(tiempo_wait_for=unscheduled_task.uid, litre_cola=True)

        # When we run unscheduled_task, dependent_task will have been queued.
        result = unscheduled_task.now()

        # Now, the dependent task will have been queued.
        task_dict_json = REDIS.lpop(dependent_task.group_key)
        task_dict = json.loads(task_dict_json)

        self.assertTrue(task_dict['kwargs_to_function'].has_key('litre_cola'))

    def test_unscheduled_task_is_unplanned(self):
        unscheduled_task = unplanned_task(some_callable)
        self.assertFalse(unscheduled_task.is_planned())

    def test_scheduled_task_is_planned(self):
        minutely = minutely_task(some_callable)
        self.assertTrue(minutely.is_planned())

    def test_minutely_task_runs_next_minute(self):
        task = minutely_task(some_callable)

        # our check time is 45 seconds after the minute
        # so the next run should be in 15 seconds at the :00 of the next minute
        delta = task.delta_until_run_time(self.check_from_time)
    
        self.assertEqual(
            delta,

            # add the minute and then set seconds to 0.
            # subtract the check time from that to get the delta
            (
                self.check_from_time +
                relativedelta(minutes=+1)
            ).replace(second=0)
            - self.check_from_time
        )

    def test_for_actual_correct_execution_time(self):
        """
            if right now is 12:30 and I schedule a task to run every hour
            on the 31st minute, it should run 15 seconds from now
            since all tasks run on the 0th second by default
        """
        task = Trabajo(periodic=True, minute=31)(some_callable)
        delta = task.delta_until_run_time(self.check_from_time)
        self.assertEqual(delta.seconds, 15)

        # self.assertEqual(delta, relativedelta(minute=40))

    '''
    Next two tests:
    Our test time is at 30 after the hour, so a task scheduled for 40
    will run this hour; a task scheduled for 20 will run next hour.
    '''
    def test_hourly_runs_this_hour(self):
        task = Trabajo(periodic=True, minute=40)(some_callable)
        delta = task.delta_until_run_time(self.check_from_time)
        self.assertEqual(delta, timedelta(minutes=9, seconds=15))

    def test_hourly_runs_next_hour(self):
        task = Trabajo(periodic=True, minute=20)(some_callable)
        delta = task.delta_until_run_time(self.check_from_time)
        self.assertEqual(delta, timedelta(minutes=49, seconds=15))

    def test_monthly_has_complete_delta(self):
        # day 4, hour 14, minute 17, second 0
        monthly = monthly_task(some_callable)
        monthly_delta = monthly.delta_until_run_time(self.check_from_time)

        # Monthly is day 4, check_from_time is day 26.
        # Since the day of our task has passed, we expect it to
        # run next month.

        self.assertEqual(monthly_delta, timedelta(days=8, hours=1, minutes=46, seconds=15))

    def test_unit_task_get_times_for_window(self):
        # task that runs on the 5th minute of every hour
        sometask = Trabajo(periodic=True, minute=5)(some_callable)

        window_begin = datetime(2006, 4, 26, 12, 30, 45)
        window_end = window_begin + timedelta(hours=1)
        times = sometask.get_times_for_window(window_begin, window_end)

        self.assertEqual(len(times), 1)
        self.assertEqual(times[0], window_begin.replace(hour=13, minute=5, second=0))

    def test_unit_task_get_times_for_window_span_days(self):
        # task that runs on the 5th minute of every hour
        sometask = Trabajo(periodic=True, minute=5)(some_callable)

        window_begin = datetime(2006, 4, 26, 20, 30, 45)
        window_end = window_begin + timedelta(hours=6)
        times = sometask.get_times_for_window(window_begin, window_end)

        self.assertEqual(len(times), 6)

        # the 1st time should be on the 5th minute of the next hour
        self.assertEqual(times[0], window_begin.replace(hour=21, minute=5, second=0))
        # the last time should be the following day
        self.assertEqual(times[-1], window_begin.replace(day=27, hour=2, minute=5, second=0))

    def test_unit_task_get_times_for_window_multi(self):
        # task that runs on the 5th minute of every hour
        sometask = Trabajo(periodic=True, minute=5)(some_callable)

        window_begin = datetime(2006, 4, 26, 12, 30, 45)
        window_end = window_begin + timedelta(hours=5)
        times = sometask.get_times_for_window(window_begin, window_end)

        self.assertEqual(len(times), 5)
        for i in range(0, 5):
            self.assertEqual(times[i], window_begin.replace(hour=13+i, minute=5, second=0))

    def test_unit_task_get_times_for_window_monthly_task(self):
        # task that runs on the 5th minute of every hour
        sometask = Trabajo(periodic=True, day=24, hour=5, minute=0)(some_callable)

        window_begin = datetime(2006, 4, 26, 12, 30, 45)
        window_end = window_begin + timedelta(days=30)
        times = sometask.get_times_for_window(window_begin, window_end)

        self.assertEqual(len(times), 1, times)
        self.assertEqual(
            times[0],
            window_begin.replace(
                # same as window begin but one month later
                month=5, day=24, hour=5, minute=0, second=0
            )
        )

    def test_unit_test_get_next_datetime_minutes(self):

        for task_minutes, check_minutes in [
                (20, 10),  # 10 minutes
                (10, 20),  # 50 minutes
                (10, 59),  # 49 minutes
                (59, 10),  # 11 minutes
                (30, 30),  # 0 minutes
                (29, 30),  # 1 minutes
                (30, 29)  # 59 minutes
            ]:

            sometask = Trabajo(periodic=True, minute=task_minutes)(some_callable)
            date_time=datetime(2006, 4, 26, 12, check_minutes, 0)

            # this is the next datetime this task should run.
            next_datetime = sometask.get_next_time_for_periodic_task(date_time)
            seconds_till_next_date_time = (next_datetime-date_time).seconds

            # figure out how many seconds from now this task should run
            # based on our current task_minutes and check_minutes
            # accounts for negative time deltas
            # ie.  10 - 20 = 50 minutes (in seconds)
            seconds_from_now_task_should_run = (3600 + relativedelta(
                minutes=task_minutes-check_minutes).minutes * 60) % 3600

            self.assertEqual(
                seconds_till_next_date_time,
                seconds_from_now_task_should_run,
                (seconds_till_next_date_time,
                seconds_from_now_task_should_run, task_minutes, check_minutes,)
            )

    def test_unit_test_get_next_datetime_hours(self):

        for task_hours, check_hours in [
                (20, 10),  # 10 hours
                (10, 20),  # 14 hours
                (12, 12),  # 0 hours
                (12, 1),  # 23 hours
                (1, 12)  # 1 hour
            ]:

            sometask = Trabajo(periodic=True, hour=task_hours)(some_callable)
            date_time=datetime(2006, 4, 26, check_hours, 0, 0)

            # this is the next datetime this task should run.
            next_datetime = sometask.get_next_time_for_periodic_task(date_time)
            seconds_till_next_date_time = (next_datetime-date_time).seconds

            # figure out how many seconds from now this task should run
            # based on our current task_hours and check_hours
            # accounts for negative time deltas
            # ie.  10 - 20 = 14 hours (in seconds)
            seconds_from_now_task_should_run = (86400 + (relativedelta(
                hours=task_hours-check_hours).hours * 60 * 60)) % 86400

            self.assertEqual(
                seconds_till_next_date_time,
                seconds_from_now_task_should_run,
                (seconds_till_next_date_time,
                seconds_from_now_task_should_run, task_hours, check_hours,)
            )

