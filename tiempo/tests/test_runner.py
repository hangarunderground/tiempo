import datetime

from twisted.trial.unittest import TestCase
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from tiempo import TIEMPO_REGISTRY
from tiempo.conn import REDIS
from tiempo.work import Trabajo, Job
from tiempo.tests.sample_tasks import some_callable
from tiempo.insight import completed_jobs
from tiempo.runner import Runner, cleanup

class RunnerTests(TestCase):
    """
    Tests for Tiempo's Runner class
    """
    decorated = Trabajo()(some_callable)
    simple_job = decorated.just_spawn_job()

    def setup(self):
        TIEMPO_REGISTRY.clear()
        REDIS.flushdb()
        reactor.run()

    def test_action_time_is_datetime(self):
        runner = Runner(0, [1])
        self.assertIsInstance(runner.action_time, datetime.datetime)

    def test_runner_is_busy(self):
        runner = Runner(0, [1])
        self.assertEqual(runner.cycle(), 300)
        job = self.simple_job.soon()
        result = runner.cycle()
        self.assertIsInstance(result, Deferred)
        self.assertEqual(runner.cycle(), 500)
        self.assertEqual(runner.cycle(), 500)
        result.addBoth(cleanup, (runner))
        return

    def test_runner_cleanup(self):
        def check(result):
            self.assertEqual(runner.currenct_job, None)
            self.assertEqual(runner.start_time, None)
            self.assertEqual(runner.finish_time, None)
            self.assertEqual(runner.error_state, False)
        runner = Runner(1, [1])
        job =self.simple_job.soon()
        result = runner.cycle()
        self.assertIsInstance(result, Deferred)
        result.addBoth(cleanup, (runner))
        result.addCallback(check)
        return
