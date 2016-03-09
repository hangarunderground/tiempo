from twisted.trial.unittest import TestCase
from tiempo import TIEMPO_REGISTRY
from tiempo.exceptions import JobDataError
from tiempo.tests.sample_tasks import some_callable
from tiempo.work import Trabajo


class ExecutionTests(TestCase):
    """
    Tests for running callables.
    """
#    decorated = Trabajo()(some_callable)
#    simple_job = decorated.just_spawn_job()

    def test_no_function_raises_error(self):
        task = Trabajo()
        self.assertRaises(JobDataError, task.get_function)
        self.assertRaises(JobDataError, task.spawn_job_and_run_now)

    def test_importing_function(self):
        decorated = Trabajo()(some_callable)
        self.assertIdentical(decorated.get_function(), some_callable)

    def test_spawn_job_raises_error(self):

        decorated = Trabajo()
        self.assertRaises(JobDataError, decorated.just_spawn_job)
        self.assertRaises(JobDataError, decorated.spawn_job_and_run_soon)
        self.assertRaises(JobDataError, decorated.soon)
        self.assertRaises(JobDataError, decorated.now)

    def test_now_imports_function(self):
        decorated = Trabajo()(some_callable, True)
        self.assertTrue(decorated.spawn_job_and_run_now())
        self.assertTrue(decorated.now())

    def test_setup_adds_task_to_tiempo_registry(self):
        decorated = Trabajo()(some_callable, True)
        value = TIEMPO_REGISTRY['tiempo.tests.sample_tasks.some_callable']
        self.assertEqual(value, decorated())
