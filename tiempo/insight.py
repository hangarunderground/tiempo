from collections import OrderedDict
from redis.exceptions import ResponseError
from tiempo.conn import REDIS
import json


def completed_jobs():

    keys = REDIS.keys('results*')
    pipe = REDIS.pipeline()
    for key in keys:
        pipe.hgetall(key)

    try:
        jobs_list = [job for job in pipe.execute()]
    except ResponseError:
        # TODO: Announce that one of the result keys didn't point to a hash and that we don't know what to do about it.
        raise

    uids = [key.split(":", 1)[1] for key in keys]
    jobs_and_keys_list = zip(uids, jobs_list)
    jobs_and_keys_list.sort(key=lambda job: job[1]['finish_time'])

    completed_jobs_dict = OrderedDict(jobs_and_keys_list)

    return completed_jobs_dict
