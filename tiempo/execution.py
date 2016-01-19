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


def thread_init():
    if len(THREAD_CONFIG):
        chalk.green('current time: %r' % utc_now())
        chalk.green(
            'Found %d thread(s) specified by THREAD_CONFIG' % len(THREAD_CONFIG)
        )

        for index, thread_group_list in enumerate(THREAD_CONFIG):
            runner = Runner(index, thread_group_list)

    tiempo_loop.start()
