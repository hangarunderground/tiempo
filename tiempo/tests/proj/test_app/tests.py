from django.test import TestCase, Client
from django.contrib.auth import get_user_model


class TiempoDjangoContribTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user('test', 'password')

    def test_contrib_urls(self):
        client = Client()
        client.login(name='test', password='password')
        # check if the "dashboard" view works
        response = client.get('/tiempo/')
        self.assertEqual(response.status_code, 200)
