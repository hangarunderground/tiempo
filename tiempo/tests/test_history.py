from tiempo.resource import TiempoMessageProtocol
from tiempo.tests.testing_utils import OneRunnerTestCase
from tiempo.utils import JobReport


class JobHistoryTests(OneRunnerTestCase):

    def test_jobs_reported_to_resource(self):
        d = self.make_one_task_and_one_job_for_runner()

        def see_how_jobs_are_announced_to_resource(backend_response, job_uid):
            job_list = JobReport()
            jobs = job_list[0:10]
            t = TiempoMessageProtocol()
            j = t.jobs_to_announce()
            self.assertEqual(jobs[0]['jobUid'], job_uid)

        d.addCallbacks(see_how_jobs_are_announced_to_resource, callbackKeywords={'job_uid': self.runner.current_job.uid})
        return d

    def test_lazy_evaulation(self):
        d = self.make_one_task_and_one_job_for_runner()

        def report_aftermath(backend_results, job_uid):
            job_list = JobReport()
            jobs = job_list[0:10]
            self.assertEqual(jobs[0]['jobUid'], job_uid)

        d.addCallbacks(report_aftermath, callbackKeywords={'job_uid': self.runner.current_job.uid})
        return d