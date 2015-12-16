from cStringIO import StringIO
import sys
import json

import chalk
from twisted.logger import Logger

from tiempo import tiempo_loop
from tiempo.runner import Runner
from .conf import THREAD_CONFIG, DEBUG
from tiempo.utils import utc_now

logger = Logger()


class CaptureStdOut(list):

    def __init__(self, *args, **kwargs):

        self.task = kwargs.pop('task')
        self.start_time = utc_now()

        super(CaptureStdOut, self).__init__(*args, **kwargs)

    def __enter__(self):
        if DEBUG:
            pass
            # return self
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        if DEBUG:
            # return
            pass

        self.extend(self._stringio.getvalue().splitlines())
        sys.stdout = self._stdout



    def format_output(self):

        return json.dumps(
            {
                'task': self.task.key,
                'uid': self.task.uid,
                'start_time': self.start_time.isoformat(),
                'end_time': self.timestamp.isoformat(),
                'duration': (self.timestamp - self.start_time).total_seconds(),
                'output': self
            }
        )





def thread_init():
    if len(THREAD_CONFIG):
        chalk.green('current time: %r' % utc_now())
        chalk.green(
            'Found %d thread(s) specified by THREAD_CONFIG' % len(THREAD_CONFIG)
        )

        for index, thread_group_list in enumerate(THREAD_CONFIG):
            runner = Runner(index, thread_group_list)

    tiempo_loop.start()
