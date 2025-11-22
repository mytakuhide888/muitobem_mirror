import json

from django.test import Client, SimpleTestCase, TestCase

from .models import DMReplyTemplate, AutoReplyRule, DMMessage, WebhookEvent, Job, Platform


class AdminSmokeTest(SimpleTestCase):
    def test_admin_login_page(self):
        client = Client()
        res = client.get('/admin/login/')
        self.assertEqual(res.status_code, 200)


class WebhookFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        tmpl = DMReplyTemplate.objects.create(name='t', reply_text='hi')
        AutoReplyRule.objects.create(name='r', platform=Platform.INSTAGRAM, keywords='hello', delay_minutes=0, reply_template=tmpl)

    def test_verify_and_dm_creates_job(self):
        res = self.client.get('/webhook/instagram/', {
            'hub.verify_token': 'test_token_ig',
            'hub.challenge': '1234',
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode(), '1234')

        payload = {
            'entry': [
                {'messaging': [{'sender': {'id': 'u1'}, 'message': {'text': 'hello'}}]}
            ]
        }
        res = self.client.post('/webhook/instagram/', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(WebhookEvent.objects.count(), 1)
        self.assertEqual(DMMessage.objects.count(), 1)
        self.assertEqual(Job.objects.filter(job_type=Job.Type.REPLY).count(), 1)
