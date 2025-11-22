from django.test import TestCase, Client
from django.urls import reverse


class IGURLTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_posts(self):
        resp = self.client.get(reverse('ig:posts'))
        self.assertEqual(resp.status_code, 200)

    def test_scheduled(self):
        resp = self.client.get(reverse('ig:scheduled'))
        self.assertEqual(resp.status_code, 200)
