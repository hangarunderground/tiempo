from unittest.case import TestCase
from tiempo.conn import REDIS
from tiempo.work import Trabajo
from sample_tasks import some_callable
from tiempo import TIEMPO_REGISTRY


class RegistryTests(TestCase):

    def setUp(self):
        TIEMPO_REGISTRY.clear()

    def test_task_decorator_adds_callable_to_registry(self):
        task = Trabajo(priority=1, periodic=True, force_interval=1)
        decorated = task(some_callable)  # Pushes onto registry dict

        self.assertEqual(len(TIEMPO_REGISTRY), 1)  # Our task it the only one in the dict.

        key = TIEMPO_REGISTRY.keys()[0]  # Grab the key...

        self.assertEqual(key.split('.')[-1], 'some_callable')  # And sure enough, it matches our callable.