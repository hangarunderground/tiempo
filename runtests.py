#! python

import os, sys
import tiempo
tiempo.LEAVE_DJANGO_UNSET = True

from tiempo import conf
conf.REDIS_QUEUE_DB = conf.REDIS_TEST_DB

# begin chdir armor
sys.path[:] = map(os.path.abspath, sys.path)
# end chdir armor

sys.path.insert(0, os.path.abspath(os.getcwd()))
sys.argv.append("tiempo/tests")

from twisted.scripts.trial import run
run()