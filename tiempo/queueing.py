from twisted.logger import Logger
from tiempo import TIEMPO_REGISTRY

logger = Logger()

def queue_expired_tasks(backend_events):
    """
    Takes a queue and a dict. Returns a dictionary of expired items to run now.
 
    Iterates over the events in the queue.
    If they are of type pmessage and expired; adds them to the run_now dict.
    """
    run_now = {}
    for task_string, task in TIEMPO_REGISTRY.items():
        run_now[task_string] = False

        for event in backend_events:

            if event['type'] == 'psubscribe':
                #ignore subscribe events
                continue

            #If this is a scheduled event and it has now expired....
            if event['pattern'].split(':')[1] == 'expired' and event['data'].split(':')[1] =='scheduled':

                data = event['data'].split(':')
                # ...then it's time to run the corresponding task.
                task_key_that_expired = data[2]
                run_now[task_key_that_expired] = True
                logger.info("Heard expiry %s." % data)

    return run_now

def queue_jobs(run_now):
    queued_jobs = {}
    for candidate, go_flag in run_now.items():
        if go_flag:
            task = TIEMPO_REGISTRY[candidate]
            queued_jobs[candidate] = task.spawn_job_and_run_soon()
        else:
            queued_jobs[candidate] = False
    return queued_jobs
