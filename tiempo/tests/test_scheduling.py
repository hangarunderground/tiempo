import json
import uuid
from tiempo import TIEMPO_REGISTRY, tiempo_loop
from datetime import datetime
from dateutil.relativedelta import relativedelta

from twisted.trial.unittest import TestCase

from sample_tasks import some_callable
from tiempo.conn import REDIS
from tiempo.utils import namespace, utc_now
from tiempo.work import Trabajo

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

    def test_minutely_tasks_expire_in_60_seconds(self):
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
        delta = task.delta_until_run_time(self.check_from_time)
        self.assertEqual(delta, relativedelta(minutes=+1))

    '''
    Next two tests:
    Our test time is at 30 after the hour, so a task scheduled for 40
    will run this hour; a task scheduled for 20 will run next hour.
    '''
    def test_hourly_runs_this_hour(self):
        task = Trabajo(periodic=True, minute=40)(some_callable)
        delta = task.delta_until_run_time(self.check_from_time)
        self.assertEqual(delta, relativedelta(minute=40))

    def test_hourly_runs_next_hour(self):
        task = Trabajo(periodic=True, minute=20)(some_callable)
        delta = task.delta_until_run_time(self.check_from_time)
        self.assertEqual(delta, relativedelta(hours=+1, minute=20))

    def test_monthly_has_complete_delta(self):
        monthly = monthly_task(some_callable)
        monthly_delta = monthly.delta_until_run_time(self.check_from_time)

        # Monthly is day 4, check_from_time is day 26.
        # Since the day of our task has passed, we expect it to
        # run next month.
        self.assertEqual(monthly_delta, relativedelta(months=+1, day=4, hour=14, minute=17))

