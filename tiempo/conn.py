import redis
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


def hear_from_backend():
    events = []
    def parse_backend():
        try:
            message = NOTIFY_PUBSUB.parse_response()
        except AttributeError, e:
            if e.args[0] == "'NoneType' object has no attribute 'can_read'":
                logger.warn("Tried to listen to redis pubsub that wasn't subscribed.")
            return events
        if message:
            event = NOTIFY_PUBSUB.handle_message(message)
            events.append(event)
        return events
    return parse_backend
