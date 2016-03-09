import json
from calendar import timegm

from twisted.internet import threads
from twisted.logger import Logger

from constants import BUSY, IDLE
from hendrix.contrib.async.messaging import hxdispatcher
from tiempo import RUNNERS
from tiempo.conn import REDIS
from tiempo.utils import utc_now, namespace
from tiempo.work import Job

logger = Logger()
from twisted.internet import defer


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

    def cycle(self, block=False):
        '''
        Tries to find a job and run it.
        If this runner already has a job, returns BUSY.
        If this runner has no job and there is none to be found, returns IDLE.

        If this runner finds a new job right now:
            returns a Deferred for that job's run(),
            with handle_success and handle_failure as finishing logic.

            If block is False, which is the sensible option most of the time,
                the Deferred is called on a thread.

            If bock is True, which makes sense for manual use cases and tests,
                the Deferred is executed immediately in the calling thread.

        patrolled 2.0
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
            # If we did get a job, we're ready to adopt it.
            self.action_time = utc_now()
            self.current_job = job = Job.rehydrate(job_string)
            logger.info("%s adopting %s" % (self, job))

            if not block:
                d = threads.deferToThread(self.run)
            else:
                d = defer.execute(self.run)
            d.addCallbacks(self.handle_success, self.handle_failure)
            d.addBoth(self.cleanup)
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

        patrolled 2.0
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
        patrolled 2.0
        """
        self.finish_time = utc_now()
        self.result_dict = self.serialize_to_dict()

        self.result_dict.update({'result': self.announcer.results_brief})  # TODO: Make announcer optional
        self.result_dict.update({'result_detail': json.dumps(self.announcer.results_detail)})

        with REDIS.pipeline() as pipe:
            backend_response = self.push_disposition_to_backend('s')  # s for success
        # TODO: Add some kind of trim or expiry here so that results:* don't grow huge.

        return backend_response

    def handle_failure(self, failure):
        """
        A callback to handle a failed attempt at running a job
        patrolled 2.0
        """
        self.finish_time = utc_now()
        self.error_state = True
        logger.info("%s at %s".format(failure.getErrorMessage(), failure.frames[-1]))  # TODO: What level do we want this to be?

        self.result_dict = self.serialize_to_dict()
        self.result_dict.update({'result': str(failure.value)})
        detail = self.result_dict['result_detail'] = self.announcer.results_detail
        detail.append(str(failure.getTraceback()))
        backend_response = self.push_disposition_to_backend('f')  # f for failure
        return backend_response

    def cleanup(self, backend_response):
        """
        Takes a backend response (typically generated by handle_success or handle_failure).
        Resets the runner to ready state.
        Returns the backend_response.

        patrolled 2.0
        """

        self.current_job.finish()

        self.current_job = self.start_time = self.finish_time = None

        self.error_state = False
        self.announce('runners')  # Announce that the runner is back to idle.
        return backend_response # And go back to cycling.

    def push_disposition_to_backend(self, result_abbreviation):
        """
        Saves result of run in backend.

        patrolled 2.0
        """
        with REDIS.pipeline() as pipe:
            now_timestamp = timegm(utc_now().utctimetuple())
            pipe.zadd("results:%s" % self.current_job.task.key, now_timestamp, "s:%s" % self.current_job.uid)
            pipe.zadd("all_results", now_timestamp, "%s:%s" % (result_abbreviation, self.current_job.uid))
            pipe.hmset('%s:%s' % (result_abbreviation, self.current_job.uid), self.result_dict)
            backend_response = pipe.execute()
        return backend_response

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
        Removes the runner from availability and reduces its references by 1.
        patrolled 2.0
        """
        for runner_list in RUNNERS.values():
            if self in runner_list:
                runner_list.remove(self)
        del self
