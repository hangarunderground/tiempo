import redis
from collections import deque
from twisted.logger import Logger
from .conf import REDIS_HOST, REDIS_PORT, REDIS_QUEUE_DB, REDIS_PW

logger = Logger()
REDIS = redis.StrictRedis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_QUEUE_DB,
    password=REDIS_PW
)

NOTIFY_PUBSUB = REDIS.pubsub()


def subscribe_to_backend_notifications(db=REDIS_QUEUE_DB):
    REDIS.config_set('notify-keyspace-events', 'KEA')
    NOTIFY_PUBSUB.psubscribe('__keyspace@%s__:results*' % db)
    NOTIFY_PUBSUB.psubscribe('__keyevent@%s__:expired' % db)


def create_event_queue():
    """
    Returns a closure that updates and returns the events queue
    """
    events = deque([])
    def update_event_queue():
        """
        A function that updates the events queue and returns it
        """
        try:
            message = NOTIFY_PUBSUB.parse_response(block=False)
        except AttributeError, e:
            if e.args[0] == "'NoneType' object has no attribute 'can_read'":
                logger.warn("Tried to listen to redis pubsub that wasn't subscribed.")
            return events
        if message:
            event = NOTIFY_PUBSUB.handle_message(message)
            events.append(event)
        return events
    return update_event_queue

def check_backend():
    """
    A syncronous alternative for update_event_queue.
    Parses all events and returns them as a list.
    """
    events = []
    while True:
        message = NOTIFY_PUBSUB.parse_response(block=False)
        if message:
            event = NOTIFY_PUBSUB.handle_message(message)
            events.append(event)
        return events
