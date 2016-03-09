from collections import OrderedDict
from hendrix.contrib.async.resources import MessageHandlerProtocol
from hendrix.contrib.async.messaging import hxdispatcher
import json


class TiempoMessageProtocol(MessageHandlerProtocol):

    def jobs_to_announce(self):
        # unsettings workaround
        from tiempo.utils import JobReport

        jobs = JobReport()[:50]
        return jobs

    def dataReceived(self, data):
        # Unsettings workaround
        from tiempo.insight import completed_jobs

        if data == "updateJobs":
            # TODO: Better way to announce jobs
            hxdispatcher.send('results', {'results': self.jobs_to_announce()})
        else:
            return MessageHandlerProtocol.dataReceived(self, data)