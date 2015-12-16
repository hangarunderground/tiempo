from twisted.logger import Logger
from tiempo.conn import REDIS

logger = Logger()


class Announcer(object):

    progress_increments = None
    progress = 0

    def __init__(self):
        super(Announcer, self).__init__()
        self.results_brief = []
        self.results_detail = []

    def set_progress_increments(self, progress_increments):
        self.progress_increments = progress_increments

    def report_progress(self, progress):
        self.progress = progress

    def brief(self, message):
        self.results_brief.append(message)

    def detail(self, message):
        self.results_detail.append(message)


def subscribe_to_channel(key):
    ps = REDIS.pubsub()
    ps.psubscribe('__keyspace__@*:%s*' % key)
    return ps.listen()
