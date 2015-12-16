from twisted.trial.unittest import TestCase
import time
from tiempo.conn import REDIS, hear_from_backend, subscribe_to_backend_notifications


class EventsBroadCastTests(TestCase):

    def test_subscribing_causes_notifications(self):
        REDIS.flushall()
        REDIS.config_set('notify-keyspace-events', '')
        REDIS.config_get('notify-keyspace-events')
        # Notifications are now turned off.

        # However, subscribing turns them back on.
        subscribe_to_backend_notifications()
        config = REDIS.config_get('notify-keyspace-events')
        self.assertEqual(config['notify-keyspace-events'], 'AKE')

    def test_subscribe_notice(self):
        REDIS.flushall()
        subscribe_to_backend_notifications()
        time.sleep(.1)

        subscribe_event = hear_from_backend()[0]
        self.assertEqual(subscribe_event['type'], 'psubscribe')

    def test_result_is_properly_reported(self):
        REDIS.flushall()
        subscribe_to_backend_notifications()

        REDIS.set('results:whatever', 'a large farva')

        try:
            # Get the third event; the first two will be subscribe notices.
            set_event = hear_from_backend()[2]
        except IndexError:
            self.fail("Didn't get more than one item from the backend.  Did you remember to enable the proper notifications?")
        key = set_event['channel'].split(':', 1)[1]
        new_value = REDIS.get(key)

        self.assertEqual(new_value, 'a large farva')