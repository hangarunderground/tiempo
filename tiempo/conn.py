import redis
from .conf import REDIS_HOST, REDIS_PORT, REDIS_QUEUE_DB, REDIS_PW


REDIS = redis.StrictRedis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_QUEUE_DB, password=REDIS_PW
)
