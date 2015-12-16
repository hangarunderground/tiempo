import random
import string

from twisted.trial.unittest import TestCase

from six.moves.queue import Queue
from tiempo.conn import REDIS
from tiempo.runner import Runner
from tiempo.utils import namespace
from tiempo.work import Trabajo
from tiempo import tiempo_loop, TIEMPO_REGISTRY


random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

q = Queue()


def unblocker():
    q.put(random_string)


class TestTaskInQueue(TestCase):

    def setUp(self):
        REDIS.flushall()

    def tearDown(self):
        self.runner.shut_down()
        TIEMPO_REGISTRY.clear()

    def test_running_without_current_job_raises_valueerror(self):
        self.runner = Runner(1, [('1')])
        self.assertIsNone(self.runner.current_job)
        # The runner has no current job, so we expect running it to raise ValueError.
        self.assertRaises(ValueError, self.runner.run)

    def test_task_is_in_queue(self):
        decorated = Trabajo()(unblocker)  # Pushes onto registry dict

        self.runner = Runner(1, [('1')])

        task_data_string = REDIS.lpop(namespace(1))
        self.assertIsNone(task_data_string)  # We haven't loaded the task into REDIS yet.

        decorated.spawn_job_and_run_soon()  # Now it's in there.
        d = self.runner.cycle()  # Run the next task in line, which we hope to be the above.

        def assert_that_unblocker_ran(n):
            unblocked_code = q.get()  # The q will have pushed the random string.
            self.assertEqual(unblocked_code, random_string)

        d.addCallback(assert_that_unblocker_ran)

        return d

