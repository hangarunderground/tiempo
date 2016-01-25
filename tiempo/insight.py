from collections import OrderedDict
from redis.exceptions import ResponseError
from tiempo.conn import REDIS
from tiempo.locks import insight_pipe_lock


def completed_jobs():
    """
    Takes no arguments, gets keys from redis, creates a pipeline and runs jobs,
    and returns an ordered dictionary of keys and jobs.
    """

    insight_pipe_lock.acquire()
    keys = REDIS.keys('results*')
    pipe = REDIS.pipeline()
    for key in keys:
        pipe.hgetall(key)

    try:
        jobs_list = [job for job in pipe.execute()]
        insight_pipe_lock.release()
    except ResponseError:
        insight_pipe_lock.release()
        # TODO: Announce that one of the result keys didn't point to a hash and that we don't know what to do about it.
        raise

    uids = [key.split(":", 1)[1] for key in keys]
    jobs_and_keys_list = zip(uids, jobs_list)
    jobs_and_keys_list.sort(key=lambda job: job[1]['finish_time'])

    completed_jobs_dict = OrderedDict(jobs_and_keys_list)

    return completed_jobs_dict
