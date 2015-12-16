from collections import OrderedDict
from hendrix.contrib.async.resources import MessageHandlerProtocol
from hendrix.contrib.async.messaging import hxdispatcher
import json


class TiempoMessageProtocol(MessageHandlerProtocol):

    def dataReceived(self, data):
        # Unsettings workaround
        from tiempo.utils import all_jobs
        from tiempo.work import Job
        from tiempo.conn import REDIS
        from tiempo.insight import completed_jobs

        if data == "updateJobs":
            # TODO: Better way to announce jobs
            jobs_to_announce = OrderedDict()
            jobs_dict = all_jobs([1, 2, 3])
            for job_list in jobs_dict.values():
                for job_string in job_list:
                    job = Job.rehydrate(job_string)
                    jobs_to_announce[job.uid] = job.serialize_to_dict()
            hxdispatcher.send('all_tasks', {'jobs': jobs_to_announce})

            # All completed jobs. # TODO: Move these things to their own place.
            all_completed = completed_jobs()
            hxdispatcher.send('results', {'results': all_completed})
        else:
            return MessageHandlerProtocol.dataReceived(self, data)