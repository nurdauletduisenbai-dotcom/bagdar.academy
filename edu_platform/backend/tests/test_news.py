import json
from datetime import timedelta
from unittest import mock
from urllib.parse import quote

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.news.models import Post

URL = '/api/v1/news/posts/'

# 1×1 PNG
PNG = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
       b'\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')


@pytest.mark.django_db
class TestPublicNews:
    def test_guest_sees_only_published(self, api):
        Post.objects.create(title='Опубликовано', body='Текст', is_published=True)
        Post.objects.create(title='Черновик', body='Текст', is_published=False)
        Post.objects.create(title='Отложено', body='Текст', is_published=True,
                            published_at=timezone.now() + timedelta(days=1))

        res = api.get(URL)
        assert res.status_code == 200
        assert [p['title'] for p in res.data['results']] == ['Опубликовано']
        assert 'body' not in res.data['results'][0]

    def test_detail_by_unicode_slug_and_draft_hidden(self, api):
        post = Post.objects.create(title='Жаңа оқу жылы', body='Бірінші абзац.\n\nЕкінші.', is_published=True)
        draft = Post.objects.create(title='Скрытая', body='x', is_published=False)
        assert post.slug == 'жаңа-оқу-жылы'

        res = api.get(f'{URL}{quote(post.slug)}/')
        assert res.status_code == 200
        assert res.data['body'].startswith('Бірінші')
        assert api.get(f'{URL}{quote(draft.slug)}/').status_code == 404

    def test_slug_is_unique_and_summary_falls_back_to_body(self):
        a = Post.objects.create(title='Итоги', body='слово ' * 100)
        b = Post.objects.create(title='Итоги', body='x', excerpt='Кратко')
        assert a.slug != b.slug
        assert a.summary.endswith('…') and len(a.summary) <= 220
        assert b.summary == 'Кратко'

    def test_pinned_first_and_ignores_invalid_token(self, api):
        Post.objects.create(title='Старая закреплённая', body='x', is_published=True, is_pinned=True,
                            published_at=timezone.now() - timedelta(days=10))
        Post.objects.create(title='Свежая', body='x', is_published=True)

        api.credentials(HTTP_AUTHORIZATION='Bearer broken')  # публичный эндпоинт не проверяет токен
        res = api.get(URL)
        assert res.status_code == 200
        assert [p['title'] for p in res.data['results']] == ['Старая закреплённая', 'Свежая']

    def test_cover_served_publicly(self, api, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        post = Post.objects.create(title='С обложкой', body='x', is_published=True,
                                   cover=SimpleUploadedFile('c.png', PNG, content_type='image/png'))
        item = api.get(URL).data['results'][0]
        assert item['cover_url']

        res = api.get(item['cover_url'])
        assert res.status_code == 200
        assert res['Content-Type'] == 'image/png'
        assert b''.join(res.streaming_content) == PNG
        assert api.get(f'{URL}{quote(Post.objects.create(title="Без", body="x", is_published=True).slug)}/cover/').status_code == 404
        assert post.cover.name.startswith('news/')

    def test_stats(self, api, make_user, org, course):
        make_user('s1@a.kz', 'student', org)
        make_user('t1@a.kz', 'teacher', org)
        res = api.get('/api/v1/news/stats/')
        assert res.status_code == 200
        assert res.data['students'] == 1 and res.data['teachers'] == 1 and res.data['schools'] >= 1


@pytest.mark.django_db
class TestContactRequest:
    URL = '/api/v1/news/contact/'

    def test_guest_can_leave_request(self, api):
        from apps.news.models import ContactRequest

        res = api.post(self.URL, {'name': 'Айгерим', 'phone': '+7 (701) 123-45-67', 'audience': 'parent',
                                  'message': 'Есть ли курсы для 9 класса?', 'language': 'kk', 'consent': True})
        assert res.status_code == 201
        req = ContactRequest.objects.get()
        assert req.audience == 'parent' and req.language == 'kk' and not req.is_processed

    def test_requires_consent_and_valid_phone(self, api):
        res = api.post(self.URL, {'name': 'Айгерим', 'phone': '12', 'consent': False})
        assert res.status_code == 400
        details = res.data['error']['details']
        assert 'phone' in details and 'consent' in details

    def test_rate_limited_per_ip(self, api, settings):
        from django.core.cache import cache
        from rest_framework.throttling import ScopedRateThrottle

        cache.clear()
        rates = {**ScopedRateThrottle.THROTTLE_RATES, 'public_form': '2/hour'}
        with mock.patch.object(ScopedRateThrottle, 'THROTTLE_RATES', rates):
            payload = {'name': 'Тест', 'phone': '+77011234567', 'consent': True}
            assert api.post(self.URL, payload).status_code == 201
            assert api.post(self.URL, payload).status_code == 201
            assert api.post(self.URL, payload).status_code == 429
        cache.clear()


@pytest.mark.django_db
class TestContactRequestNotify:
    URL = '/api/v1/news/contact/'
    PAYLOAD = {'name': 'Айгерим', 'phone': '+77011234567', 'audience': 'parent',
               'message': 'Есть ли курсы?', 'language': 'kk', 'consent': True}

    @pytest.fixture
    def leads(self, settings):
        settings.LEADS_TELEGRAM_BOT_TOKEN = '123:test'
        settings.LEADS_TELEGRAM_CHAT_ID = '-100500'
        settings.LEADS_NOTIFY_EMAILS = ['team@bagdar.academy', 'sales@bagdar.academy']
        return settings

    def _post(self, api, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            return api.post(self.URL, self.PAYLOAD)

    def test_sends_telegram_and_email(self, api, leads, mailoutbox, django_capture_on_commit_callbacks):
        response = mock.MagicMock(status=200)
        with mock.patch('apps.news.tasks.urllib.request.urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = response
            res = self._post(api, django_capture_on_commit_callbacks)

        assert res.status_code == 201
        request = urlopen.call_args.args[0]
        assert request.full_url == 'https://api.telegram.org/bot123:test/sendMessage'
        body = json.loads(request.data)
        assert body['chat_id'] == '-100500'
        assert 'Айгерим' in body['text'] and '+77011234567' in body['text'] and 'Родитель' in body['text']
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ['team@bagdar.academy', 'sales@bagdar.academy']
        assert 'Есть ли курсы?' in mailoutbox[0].body

    def test_nothing_configured_does_nothing(self, api, settings, mailoutbox, django_capture_on_commit_callbacks):
        settings.LEADS_TELEGRAM_BOT_TOKEN = ''
        settings.LEADS_TELEGRAM_CHAT_ID = ''
        settings.LEADS_NOTIFY_EMAILS = []
        with mock.patch('apps.news.tasks.urllib.request.urlopen') as urlopen, \
                mock.patch('apps.news.tasks.notify_new_contact_request.delay') as delay:
            res = self._post(api, django_capture_on_commit_callbacks)
        assert res.status_code == 201
        delay.assert_not_called()
        urlopen.assert_not_called()
        assert mailoutbox == []

    def test_telegram_failure_still_sends_email(self, api, leads, mailoutbox, django_capture_on_commit_callbacks):
        with mock.patch('apps.news.tasks.urllib.request.urlopen', side_effect=OSError('network down')):
            res = self._post(api, django_capture_on_commit_callbacks)
        assert res.status_code == 201
        assert len(mailoutbox) == 1

    def test_all_channels_failing_never_breaks_form(self, api, leads, django_capture_on_commit_callbacks):
        from apps.news.models import ContactRequest

        with mock.patch('apps.news.tasks.urllib.request.urlopen', side_effect=OSError('network down')), \
                mock.patch('apps.news.tasks.send_mail', side_effect=OSError('smtp down')):
            res = self._post(api, django_capture_on_commit_callbacks)
        assert res.status_code == 201
        assert ContactRequest.objects.count() == 1

    def test_broker_down_never_breaks_form(self, api, leads, django_capture_on_commit_callbacks):
        with mock.patch('apps.news.tasks.notify_new_contact_request.delay', side_effect=ConnectionError('redis')):
            res = self._post(api, django_capture_on_commit_callbacks)
        assert res.status_code == 201
