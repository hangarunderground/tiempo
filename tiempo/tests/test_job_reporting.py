import datetime

from twisted.trial.unittest import TestCase
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from tiempo import TIEMPO_REGISTRY
from tiempo.conn import REDIS
from tiempo.exceptions import JobDataError
from tiempo.tests.testing_utils import OneRunnerTestCase
from tiempo.work import Trabajo, Job
from tiempo.tests.sample_tasks import some_callable
from tiempo.insight import completed_jobs
from tiempo.runner import Runner

import unittest


class JobReportingTests(OneRunnerTestCase):
    """
    Tests for Job instances and report_handlers
    """

#    def __init__(self):
    decorated = Trabajo()(some_callable)
    simple_job = decorated.just_spawn_job()

    def setup(self):
        TIEMPO_REGISTRY.clear()
        REDIS.flushall()

    def test_just_spawn_job_is_Job(self):
        self.assertIsInstance(self.simple_job, Job)

    def test_freeze(self):
        dictionary = self.simple_job.freeze()
        self.assertIsInstance(dictionary, dict)
        uid = dictionary['uid']
        self.assertIsInstance(uid, str)
        dictionary = self.simple_job.freeze(make_frozen=False)
        self.assertRaises(ValueError, f=self.simple_job.enqueue)

    def test_job_finish_without_being_started_raises_error(self):
        self.assertRaises(JobDataError, self.simple_job.finish)

    def test_show_no_completed_jobs(self):
        cj = completed_jobs()
        self.assertFalse(cj)

    @unittest.skip("completed_jobs not operational")
    def test_show_some_completed_jobs(self):
        job = self.decorated.spawn_job_and_run_soon()
        d = self.runner.cycle()

        def check(result, job):
            cj = completed_jobs()
            self.assertTrue(cj)

        d.addCallback(check, job)
        return d
