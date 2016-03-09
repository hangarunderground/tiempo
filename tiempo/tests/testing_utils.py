from twisted.internet.defer import gatherResults
from twisted.trial.unittest import TestCase
from tiempo import TIEMPO_REGISTRY
from tiempo.conn import REDIS
from tiempo.runner import Runner
from tiempo.tests.sample_tasks import some_callable
from tiempo.utils.premade_decorators import hourly_task


class OneRunnerTestCase(TestCase):

    def setUp(self):
        super(OneRunnerTestCase, self).setUp()
        REDIS.flushall()
        self.runner = Runner(0, [1])

    def tearDown(self):
        self.runner.shut_down()
        REDIS.flushall()
        TIEMPO_REGISTRY.clear()
        super(OneRunnerTestCase, self).tearDown()

    def make_one_task_and_one_job_for_runner(self, f=some_callable):
        task = hourly_task(f)
        job = task.spawn_job_and_run_soon()
        d = self.runner.cycle()
        return d

    def make_one_task_and_many_jobs_for_runner(self, number_of_jobs):
        self.task = hourly_task(some_callable)
        self.jobs = []
        self._deferred_list = []
        for i in range(number_of_jobs):
            self.jobs.append(self.task.spawn_job_and_run_soon())
            self._deferred_list.append(self.runner.cycle(block=True))
        self.combo_deferred = gatherResults(self._deferred_list)
        return self.combo_deferred
