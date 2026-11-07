import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.organizations.models import Invite, OrgMembership
from apps.schools import applications
from apps.schools.models import Region, School, SchoolApplication

User = get_user_model()
URL = '/api/v1/schools/applications/'
PASSWORD = 'StrongPassword123!'


@pytest.fixture
def almaty(db):
    return Region.objects.get(code='KZ-75')


@pytest.fixture
def school(almaty):
    return School.objects.create(name='№ 39 мектеп-лицей', name_ru='Школа-лицей № 39', region=almaty,
                                 locality='Алматы')


def payload(**extra):
    return {'org_type': 'school', 'contact_name': 'Сәуле Ахметова', 'position': 'Директор',
            'email': 'Director@School39.kz', 'phone': '+7 701 123 45 67', 'students_count': 800,
            'bin': '123456789012', 'language': 'ru', 'consent': True, **extra}


def apply(api, **extra):
    return api.post(URL, payload(**extra), format='json')


@pytest.mark.django_db
class TestSubmit:
    def test_directory_school_application(self, api, school):
        assert apply(api, school_id=school.id).status_code == 201
        app = SchoolApplication.objects.get()
        assert (app.school, app.email, app.status, app.is_claim) == (school, 'director@school39.kz', 'new', False)

    def test_one_pending_application_per_school_and_email(self, api, school):
        assert apply(api, school_id=school.id).status_code == 201
        again = apply(api, school_id=school.id, email='director@school39.kz')
        assert again.status_code == 400 and 'email' in again.data['error']['details']

    def test_own_school_is_added_for_review(self, api, almaty):
        res = apply(api, org_type='center', new_school={'name': 'Bilim Plus оқу орталығы', 'kind': 'center',
                                                        'region': almaty.id, 'locality': 'Алматы'})
        assert res.status_code == 201
        school = SchoolApplication.objects.get().school
        assert (school.name, school.is_approved, school.source) == ('Bilim Plus оқу орталығы', False, 'user')

    def test_validation(self, api, school, almaty):
        bad = apply(api, school_id=school.id, bin='123', phone='12', consent=False).data['error']['details']
        assert {'bin', 'phone', 'consent'} <= set(bad)
        both = apply(api, school_id=school.id, new_school={'name': 'Ещё одна', 'region': almaty.id})
        none = apply(api)
        assert both.status_code == none.status_code == 400

    def test_claim_flag_when_school_already_has_admin(self, api, school, make_user):
        from apps.schools.services import ensure_organization
        org = ensure_organization(school)
        make_user('boss@a.kz', 'admin', org)
        apply(api, school_id=school.id)
        assert SchoolApplication.objects.get().is_claim is True


@pytest.mark.django_db
class TestReview:
    def _app(self, api, school, **extra):
        apply(api, school_id=school.id, **extra)
        return SchoolApplication.objects.get()

    def test_approve_new_applicant_gets_admin_invite_and_can_register(self, api, school, mailoutbox,
                                                                      django_capture_on_commit_callbacks):
        reviewer = User.objects.create_superuser(email='root@edu.local', password=PASSWORD, first_name='S', last_name='A')
        app = self._app(api, school)
        with django_capture_on_commit_callbacks(execute=True):
            result = applications.approve(app, reviewer)
        assert result['invited'] is True
        app.refresh_from_db()
        school.refresh_from_db()
        assert app.status == 'approved' and app.reviewed_by == reviewer
        invite = Invite.objects.get()
        assert (invite.org, invite.role, invite.max_uses) == (school.organization, 'admin', 1)

        assert mailoutbox[-1].to == ['director@school39.kz']
        token = re.search(r'/invite\?token=(\S+)', mailoutbox[-1].body).group(1)
        reg = api.post('/api/v1/auth/register-by-invite/', {
            'invite_token': token, 'email': 'director@school39.kz', 'password': PASSWORD,
            'first_name': 'Сәуле', 'last_name': 'Ахметова'})
        assert reg.status_code == 201
        assert OrgMembership.objects.filter(org=school.organization, user__email='director@school39.kz',
                                            role='admin', is_active=True).exists()

    def test_approve_existing_user_gets_role_at_once_and_sees_earlier_students(
            self, api, school, make_user, mailoutbox, django_capture_on_commit_callbacks):
        from apps.schools.services import set_student_school
        student = make_user('pupil@a.kz')
        set_student_school(student, school)  # ученик выбрал школу раньше, чем она подключилась
        director = make_user('director@school39.kz')
        app = self._app(api, school, language='kk')

        with django_capture_on_commit_callbacks(execute=True):
            result = applications.approve(app, None)
        assert result['invited'] is False and not Invite.objects.exists()
        org = school.organization if school.organization_id else School.objects.get(pk=school.pk).organization
        assert OrgMembership.objects.filter(org=org, user=director, role='admin').exists()
        assert OrgMembership.objects.filter(org=org, user=student, role='student').exists()
        assert 'мақұлданды' in mailoutbox[-1].subject  # письмо на языке заявителя

    def test_approving_pending_own_school_lists_it(self, api, almaty):
        apply(api, new_school={'name': 'Робототехника үйірмесі', 'kind': 'club', 'region': almaty.id})
        app = SchoolApplication.objects.get()
        applications.approve(app, None)
        app.school.refresh_from_db()
        assert app.school.is_approved and app.school.organization_id

    def test_cannot_approve_twice(self, api, school):
        app = self._app(api, school)
        applications.approve(app, None)
        with pytest.raises(Exception):
            applications.approve(app, None)

    def test_reject_and_request_info_send_the_note(self, api, school, mailoutbox, django_capture_on_commit_callbacks):
        app = self._app(api, school)
        with pytest.raises(Exception):
            applications.request_info(app, None)  # без текста уточнения нельзя
        app.review_note = 'Пришлите, пожалуйста, приказ о назначении.'
        app.save()
        with django_capture_on_commit_callbacks(execute=True):
            applications.request_info(app, None)
        assert 'приказ о назначении' in mailoutbox[-1].body
        app.review_note = ''
        app.save()
        with django_capture_on_commit_callbacks(execute=True):
            applications.reject(app, None)
        app.refresh_from_db()
        assert app.status == 'rejected' and 'не удалось подтвердить' in mailoutbox[-1].body

    def test_admin_action_approves(self, api, admin_client, school):
        app = self._app(api, school)
        res = admin_client.post('/admin/schools/schoolapplication/', {'action': 'approve',
                                                                     '_selected_action': [app.id]})
        assert res.status_code == 302
        app.refresh_from_db()
        assert app.status == 'approved' and Invite.objects.filter(role='admin').exists()


@pytest.mark.django_db
class TestManageOnSite:
    MANAGE = '/api/v1/schools/applications/manage/'

    @pytest.fixture
    def root(self, auth_client):
        user = User.objects.create_superuser(email='root@edu.local', password=PASSWORD, first_name='S', last_name='A')
        return auth_client(user)

    def test_only_superuser(self, api, auth_client, make_user, org, school):
        apply(api, school_id=school.id)
        org_admin = make_user('a@a.kz', 'admin', org)
        assert auth_client(org_admin, org.id).get(self.MANAGE).status_code == 403
        assert api.get(self.MANAGE).status_code == 401

    def test_list_summary_and_profile_flag(self, api, root, school):
        apply(api, school_id=school.id)
        res = root.get(self.MANAGE, {'status': 'new'})
        assert res.status_code == 200 and res.data['total'] == 1
        item = res.data['results'][0]
        assert item['school']['name'] == '№ 39 мектеп-лицей' and item['school']['admins'] == []
        assert root.get(f'{self.MANAGE}summary/').data == {'new': 1, 'needs_info': 0, 'approved': 0, 'rejected': 0}
        assert root.get('/api/v1/auth/users/me/').data['is_superuser'] is True

    def test_fix_data_swap_school_and_approve(self, api, root, almaty, school, mailoutbox,
                                              django_capture_on_commit_callbacks):
        apply(api, new_school={'name': '39 лицей', 'region': almaty.id})
        app = SchoolApplication.objects.get()
        url = f'{self.MANAGE}{app.id}/'
        # Опечатка в email и ФИО заявителя + правка карточки своей школы
        res = root.patch(url, {'email': 'Fixed@School39.kz', 'contact_name': '  Сәуле   Ахметова ',
                               'school_edit': {'name': 'Лицей № 39', 'kind': 'lyceum', 'locality': 'Алматы'}},
                         format='json')
        assert res.status_code == 200
        assert (res.data['email'], res.data['contact_name']) == ('fixed@school39.kz', 'Сәуле Ахметова')
        assert (res.data['school']['name'], res.data['school']['kind']) == ('Лицей № 39', 'lyceum')
        # Оказалось, школа уже есть в справочнике — заменяем
        res = root.patch(url, {'school_id': school.id}, format='json')
        assert res.data['school']['id'] == school.id

        with django_capture_on_commit_callbacks(execute=True):
            res = root.post(f'{url}approve/')
        assert res.status_code == 200 and res.data['status'] == 'approved'
        assert res.data['result']['invited'] is True and res.data['result']['org_name'] == 'Школа-лицей № 39'
        assert mailoutbox[-1].to == ['fixed@school39.kz']
        # После одобрения данные не меняются, повторно одобрить нельзя
        assert root.patch(url, {'phone': '+7 777 777 77 77'}, format='json').status_code == 400
        assert root.post(f'{url}approve/').status_code == 400
        assert root.post(f'{url}reject/').status_code == 400

    def test_reject_and_request_info_with_note_from_body(self, api, root, school, mailoutbox,
                                                          django_capture_on_commit_callbacks):
        apply(api, school_id=school.id)
        app = SchoolApplication.objects.get()
        assert root.post(f'{self.MANAGE}{app.id}/request-info/', {}, format='json').status_code == 400
        with django_capture_on_commit_callbacks(execute=True):
            res = root.post(f'{self.MANAGE}{app.id}/request-info/', {'review_note': 'Пришлите приказ.'}, format='json')
        assert res.data['status'] == 'needs_info' and 'Пришлите приказ.' in mailoutbox[-1].body
        with django_capture_on_commit_callbacks(execute=True):
            res = root.post(f'{self.MANAGE}{app.id}/reject/', {'review_note': 'Не подтвердили.'}, format='json')
        assert res.data['status'] == 'rejected' and 'Не подтвердили.' in mailoutbox[-1].body


@pytest.mark.django_db
class TestInviteLinkFromEmail:
    PREVIEW = '/api/v1/auth/invites/preview/'
    REGISTER = '/api/v1/auth/register-by-invite/'

    def _approved_link(self, api, school, mailoutbox, capture):
        apply(api, school_id=school.id, contact_name='Сәуле Ахметова Бекқызы')
        with capture(execute=True):
            applications.approve(SchoolApplication.objects.get(), None)
        return re.search(r'/invite\?token=(\S+)', mailoutbox[-1].body).group(1)

    def test_preview_prefills_and_locks_email(self, api, school, mailoutbox, django_capture_on_commit_callbacks):
        token = self._approved_link(api, school, mailoutbox, django_capture_on_commit_callbacks)
        data = api.get(self.PREVIEW, {'token': token}).data
        assert data['status'] == 'valid' and data['role'] == 'admin' and data['email_locked'] is True
        assert (data['email'], data['first_name'], data['last_name']) == \
            ('director@school39.kz', 'Сәуле', 'Ахметова Бекқызы')

    def test_only_password_needed_email_cannot_be_swapped_and_link_dies(
            self, api, school, mailoutbox, django_capture_on_commit_callbacks):
        token = self._approved_link(api, school, mailoutbox, django_capture_on_commit_callbacks)
        res = api.post(self.REGISTER, {'invite_token': token, 'email': 'attacker@evil.kz', 'password': PASSWORD,
                                       'first_name': 'Сәуле', 'last_name': 'Ахметова'})
        assert res.status_code == 201
        assert User.objects.filter(email='director@school39.kz').exists()
        assert not User.objects.filter(email='attacker@evil.kz').exists()
        # Ссылка и код больше не работают
        assert api.get(self.PREVIEW, {'token': token}).data == {'status': 'used'}
        again = api.post(self.REGISTER, {'invite_token': token, 'password': PASSWORD, 'first_name': 'X',
                                         'last_name': 'Y'})
        assert again.status_code == 400 and 'использовано' in str(again.data['error']['details']['invite_token'])

    def test_expired_and_unknown_links(self, api, school, mailoutbox, django_capture_on_commit_callbacks):
        token = self._approved_link(api, school, mailoutbox, django_capture_on_commit_callbacks)
        Invite.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        assert api.get(self.PREVIEW, {'token': token}).data == {'status': 'expired'}
        assert api.get(self.PREVIEW, {'token': 'nope'}).data == {'status': 'not_found'}
