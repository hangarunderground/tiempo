import datetime
import json

from hendrix.contrib.async.messaging import hxdispatcher
from twisted.internet import threads
from constants import BUSY, IDLE

from tiempo.conn import REDIS
from tiempo.utils import utc_now, namespace
from tiempo.work import Job
from tiempo import RUNNERS
from twisted.logger import Logger
logger = Logger()
import traceback


class Runner(object):
    '''
    Runs Jobs.

    During tiempo_loop, each runner is given a chance to run a job in the queue.
    '''

    start_time = None
    finish_time = None

    def __init__(self, number, thread_group_list):

        logger.info("Starting Runner %s for groups %s (%s)" % (number, thread_group_list, id(self)))
        for i in thread_group_list:
            if RUNNERS.has_key(i):
                RUNNERS[i].append(self)
            else:
                RUNNERS[i] = [self]

        self.action_time = utc_now()
        self.current_job = None
        self.task_groups = thread_group_list
        self.number = number
        self.error_state = False
        self.announcer = None

    def __repr__(self):
        return 'Tiempo Runner %d' % self.number

    def cycle(self):
        '''
        Try to find a job and run it.
        If this runner already has a job, returns BUSY.
        If this runner has no job and there is none to be found, return IDLE.
        If this runner finds a new job right now, return a Deferred for that job's run().
        '''

        # If we have a current Job, return BUSY and go no further.
        if self.current_job:
            logger.debug("Worker %s is busy with %s (%s / %s)" % (
                self.number,
                self.current_job.code_word,
                self.current_job.task.key,
                self.current_job.uid)
            )
            return BUSY

        # ...otherwise, look for a Job to run...,
        job_string = self.seek_job()

        if not job_string:
            # If we didn't get a job, we're IDLE.
            return IDLE
        else:
            # If we did get a job, we're ready to defer it and return the Deferred.
            self.action_time = utc_now()
            self.current_job = job = Job.rehydrate(job_string)
            logger.info("%s adopting %s" % (self, job))
            d = threads.deferToThread(self.run)
            return d

    def seek_job(self):

        for g in self.task_groups:

            logger.debug('%r checking for a Job in group %r' % (self, g))
            group_key = namespace(g)
            job_string = REDIS.lpop(group_key)
            if job_string:
                job_dict = json.loads(job_string)
                logger.info('%s found Job %s (%s) in group %s: %s' % (
                    self,
                    job_dict['codeWord'],
                    job_dict['uid'],
                    g,
                    job_dict['function_name'],
                    ))
                return job_string

    def run(self):
        '''
        Run the current job's task now.
        '''

        self.start_time = utc_now()
        try:
            logger.debug('%s running task: %s' % (self, self.current_job.code_word))
            self.announce('runners', alert=True)
            self.current_job.start()
        except AttributeError, e:
            if not getattr(self, "current_job", None):
                raise ValueError("A Runner cannot run without a current_job.")
            else:
                raise

        task = self.current_job.task
        self.announcer = self.current_job.announcer

        return task.run(runner=self)

    def handle_success(self, return_value):
        """
        A callback to handle a successful running of a job
        """
        self.finish_time = utc_now()
        runner_dict = self.serialize_to_dict()

        runner_dict.update({'result': self.announcer.results_brief})
        runner_dict.update({'result_detail': json.dumps(self.announcer.results_detail)})

        REDIS.hmset('results:%s' % self.current_job.uid, runner_dict)
        # TODO: Add some kind of trim here so that results:* don't grow huge.
        ##

        return

    def handle_error(self, failure):
        """
        A callback to handle a failed attempt at running a job
        """
        self.finish_time = utc_now()
        self.error_state = True
        logger.info(failure.getBriefTraceback())  # TODO: What level do we want this to be?
        runner_dict = self.serialize_to_dict()
        runner_dict.update({'result': str(failure.value)})
        detail = runner_dict['result_detail'] = self.announcer.results_detail
        detail.append(str(failure.getTraceback()))
        REDIS.hset('results:%s' % self.current_job.uid, runner_dict)

        return

    def serialize_to_dict(self, alert=False):

        if self.current_job:
            code_word = self.current_job.code_word
            job_uid = self.current_job.uid
        else:
            code_word = None
            job_uid = None

        if self.current_job:
            message = self.current_job.task.key
        else:
            message = "Idle"
        d = {
            'runner': self.number,
            'codeWord': code_word,
            'message_time': self.action_time.isoformat(),
            'message': message,
            'jobUid': job_uid,
            'alert': alert,
            'error': self.error_state,
        }

        if self.start_time:
            d['start_time'] = self.start_time.isoformat()
        if self.finish_time:
            d['finish_time'] = self.finish_time.isoformat()

        if self.announcer:
            if self.announcer.progress_increments:
                progress_percentage = (float(self.announcer.progress) / float(self.announcer.progress_increments)) * 100
                d['total_progress'] = progress_percentage
                logger.debug("Reporting Progress for %s as %s" % (self, progress_percentage))

        return d

    def announce(self, channel, alert=False):

        hxdispatcher.send(channel,
                          {
                              'runners':
                                  {
                                      self.number: self.serialize_to_dict(alert=alert)
                                  }
                          }
                          )

    def shut_down(self):
        """
        removes runners from RUNNERS
        RUNNERS is a dictionary
        """
        for runner_list in RUNNERS.values():
            if self in runner_list:
                runner_list.remove(self)

def cleanup(runner):
    """
    A callback for runner management.

    Creates a new runner and shutsdown the old one.
    """
    number = runner.number
    task_groups = runner.task_groups
    new_runner = Runner(number, task_groups)
    runner.shut_down
    return new_runner
