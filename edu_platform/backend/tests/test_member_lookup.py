import pytest
from django.contrib.auth import get_user_model

from apps.organizations.models import OrgMembership

User = get_user_model()
URL = '/api/v1/orgs/members/lookup/'


@pytest.fixture
def admin(make_user, org):
    return make_user('admin@a.kz', 'admin', org)


@pytest.fixture
def people(make_user, org, other_org):
    aigerim = make_user('aigerim.serik@mail.kz', 'student', org)
    arman = make_user('arman@mail.kz', 'teacher', other_org)
    User.objects.filter(id=aigerim.id).update(first_name='Айгерим', last_name='Серікова')
    User.objects.filter(id=arman.id).update(first_name='Арман', last_name='Нұрланов')
    return aigerim


@pytest.mark.django_db
class TestMemberLookup:
    def test_org_admin_finds_only_by_exact_email(self, auth_client, admin, org, people):
        client = auth_client(admin, org.id)
        found = client.get(URL, {'q': 'Arman@Mail.kz'}).data
        assert [(u['email'], u['full_name'], u['roles']) for u in found] == [('arman@mail.kz', 'Арман Нұрланов', [])]
        # Частичный запрос администратору школы ничего не раскрывает
        assert client.get(URL, {'q': 'arm'}).data == []
        assert client.get(URL, {'q': 'nobody@mail.kz'}).data == []

    def test_shows_roles_in_current_org(self, auth_client, admin, org, people):
        res = auth_client(admin, org.id).get(URL, {'q': 'aigerim.serik@mail.kz'})
        assert res.data[0]['roles'] == ['student']

    def test_superuser_searches_by_name_or_part_of_email(self, auth_client, org, people):
        root = User.objects.create_superuser(email='root@edu.local', password='StrongPassword123!',
                                             first_name='Супер', last_name='Админ')
        client = auth_client(root, org.id, header_org=org.id)
        assert [u['email'] for u in client.get(URL, {'q': 'Серік'}).data] == ['aigerim.serik@mail.kz']
        assert [u['email'] for u in client.get(URL, {'q': 'mail.kz'}).data] == ['aigerim.serik@mail.kz', 'arman@mail.kz']

    def test_teacher_cannot_lookup(self, auth_client, make_user, org, people):
        teacher = make_user('t@a.kz', 'teacher', org)
        assert auth_client(teacher, org.id).get(URL, {'q': 'arman@mail.kz'}).status_code == 403

    def test_add_found_user_as_admin(self, auth_client, admin, org, people):
        client = auth_client(admin, org.id)
        user = client.get(URL, {'q': 'arman@mail.kz'}).data[0]
        assert client.post('/api/v1/orgs/members/', {'email': user['email'], 'role': 'admin'}).status_code == 201
        assert OrgMembership.objects.filter(org=org, user_id=user['id'], role='admin', is_active=True).exists()
