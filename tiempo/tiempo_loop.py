"""
The logic for tiempo's event loop.

Twisted makes a looping call to cycle, which causes it to be running pretty much
constantly. Which means any bugs in this module will have their consequence
multiplied several times. cycle divides up its workload among several functions.
The start function begins the event loop.
"""

import calendar
from tiempo import TIEMPO_REGISTRY, all_runners

from hendrix.contrib.async.messaging import hxdispatcher
from twisted.internet import task
from twisted.logger import Logger

from constants import BUSY, IDLE
from tiempo.conn import REDIS, subscribe_to_backend_notifications, create_event_queue
from tiempo.utils import namespace, utc_now
from tiempo.work import announce_tasks_to_client
from tiempo.locks import schedule_lock
from tiempo.queueing import queue_expired_tasks, queue_jobs

logger = Logger()
ps = REDIS.pubsub()
update_queue = create_event_queue()


def cycle():
    """This function runs in the event loop for tiempo"""
    # This loop does five things:

    # Thing 1) Harvest events that have come in from the backend.
    events = glean_events_from_backend()
    # Thing 2) Let the runners pick up any queued tasks.
    let_runners_pick_up_queued_tasks()
    # Thing 3) Queue up new tasks.
    queue_scheduled_tasks(events)
    # Thing 4) Schedule new tasks for enqueing.
    #schedule_tasks_for_queueing()
    # Thing 5) Broadcast any new announcements to listeners.
    broadcast_new_announcements_to_listeners(events)

looper = task.LoopingCall(cycle)


def glean_events_from_backend():
    """
    Checks redis for pubsub events.
    """
    events = update_queue()
    return events


def let_runners_pick_up_queued_tasks():
    for runner in all_runners():

        result = runner.cycle()

        if not result in (BUSY, IDLE):
            # The runner might be BUSY (still working on a task)
            # or it might be IDLE (without a task to run and with none to pick up).
            # Otherwise, it will have JUST PICKED UP A TASK.
            # If this is the case, it will have returned a Deferred.
            # We add our paths for success and failure here.

	    # TODO: Sort this out.
            # result.addCallback(cleanup, runner)
            # result.addErrback(cleanup_errors, runner)
            pass

        runner.announce('runners')  # The runner may have changed state; announce it.
    return result

def queue_scheduled_tasks(backend_events):
    """
    Takes a list. Iterates over the events in the list.
    If they are both scheduled and expired,
    calls task.spawn_job_and_run_soon.
    """
    # TODO: What happens if this is running on the same machine?
    run_now = queue_expired_tasks(backend_events)

    # We now know which jobs need to be run.  Run them if marked.
    queue_jobs(run_now)
    return


def schedule_tasks_for_queueing():
    """
    Takes no arguments. Schedules runtimes and adds them to redis.

    Creates a redis pipeline.
    Runs Trabajo.check_schedule to check the scheduling.
    Iterates over all tasks in TIEMPO_REGISTRY
    and all of the run times of a particular task.
    For a particular run time of a particular task,
    sets that tasks value to zero, and sets an
    expire time. Sets a lattermost run time,
    acquires a lock, and executes all of the
    commands in the pipe.
    """
    pipe = REDIS.pipeline()
    for trabajo in TIEMPO_REGISTRY.values():
        # TODO: Does this belong in Trabajo?  With pipe as an optional argument?
        run_times = trabajo.check_schedule()

        for run_time in run_times:
            # TODO: There's probably a better namespace for this 
            #maybe a UUID to assigned to the job that eventually gets spawned.
            unix_time = calendar.timegm(run_time.timetuple())
            key = namespace('scheduled:%s:%s' % (trabajo.key, unix_time))
            pipe.set(key, 0)
            pipe.expireat(key, unix_time)
        if run_times:
            # After loop, set final time.
            pipe.set(namespace('last_run_time:%s' % trabajo.key), run_time.isoformat())
    if schedule_lock.acquire():
        pipe.execute()
    schedule_lock.release()


def broadcast_new_announcements_to_listeners(events):

    try:
        event = events.popleft()
    except IndexError:
        return
    if not event['type'] == 'psubscribe':
        channel = event['channel'].split(':', 1)[1]
        if channel == "expired":
            return
        try:
            key = REDIS.zrange(channel, 0, 0)[0]
        except:
            channel
        if "results" in key:
            return

        if key.startswith('s:' or 'f:'):  # This is either a success or failure notice.
            job_information = REDIS.hgetall(key)

        new_value = job_information  # TODO: what's going on here?
        channel_to_announce = key.split(':', 1)[0]
        if new_value.has_key('jobUid'):
            hxdispatcher.send(channel_to_announce,
                {channel_to_announce: {new_value['jobUid']: new_value}})
        else:
            hxdispatcher.send(channel_to_announce, {channel_to_announce: new_value})


def start():
    """
    Starts running the tiempo_loop at an interval.

    TODO 2.0: Add tuning knobs for interval times
    """

    subscribe_to_backend_notifications()

    logger.info("tiempo_loop start() called.")

    if not looper.running:
        looper.start(1)  # TODO: Customize interval
        task.LoopingCall(announce_tasks_to_client).start(5)
        task.LoopingCall(schedule_tasks_for_queueing).start(5)
    else:
        logger.warning("Tried to call tiempo_loop start() while the loop is already running.")
