from rest_framework.test import APISimpleTestCase
from tiempo.tests.testing_utils import OneRunnerTestCase


class JobHistoryApiTests(APISimpleTestCase, OneRunnerTestCase):

    def test_51_jobs_paginated(self):
        number_of_jobs = 51
	self.make_one_task_and_many_jobs_for_runner(number_of_jobs)

        number_to_display = 20
        response = self.client.get('/api/v1/jobs/?limit=20')
        # self.assertEqual(self.runner.current_job.uid, response.data['results'][0]['jobUid'])  # TODO: Move this to a test where it makes sense.
        self.assertEqual(response.data['count'], number_of_jobs)
        self.assertEqual(len(response.data['results']), 20)
