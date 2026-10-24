import pytest
from django.contrib.auth import get_user_model

from apps.organizations.models import OrgMembership
from apps.schools.importing import detect_kind, import_records
from apps.schools.models import Region, School
from apps.schools.osm import build_records

User = get_user_model()
PASSWORD = 'StrongPassword123!'
SEARCH = '/api/v1/schools/'


@pytest.fixture
def almaty(db):
    return Region.objects.get(code='KZ-75')


@pytest.fixture
def astana(db):
    return Region.objects.get(code='KZ-71')


def register(api, **extra):
    payload = {'email': 'new@a.kz', 'password': PASSWORD, 'first_name': 'Айгерим', 'last_name': 'Серікова',
               'role': 'student', **extra}
    return api.post('/api/v1/auth/register/', payload, format='json')


@pytest.mark.django_db
class TestDirectory:
    def test_twenty_regions_are_seeded(self, api):
        res = api.get('/api/v1/schools/regions/')
        assert res.status_code == 200
        assert len(res.data) == 20
        assert {'name_ru': 'Астана', 'name_kk': 'Астана'}.items() <= res.data[0].items()

    def test_search_shows_only_approved_visible_and_matches_number(self, api, almaty, astana):
        School.objects.create(name='№ 25 мектеп-гимназия', region=almaty, locality='Алматы')
        School.objects.create(name='Школа № 250', region=astana, locality='Астана')
        School.objects.create(name='№ 25 жасырын', region=almaty, is_active=False)
        School.objects.create(name='№ 25 тексеруде', region=almaty, is_approved=False)

        names = [s['name'] for s in api.get(SEARCH, {'search': '№ 25'}).data['results']]
        assert names == ['Школа № 250', '№ 25 мектеп-гимназия']  # Астана в списке регионов раньше Алматы
        only_almaty = api.get(SEARCH, {'search': '25', 'region': almaty.id}).data['results']
        assert [s['name'] for s in only_almaty] == ['№ 25 мектеп-гимназия']

    def test_connected_schools_come_first(self, api, almaty, org):
        School.objects.create(name='Лицей Б', region=almaty)
        School.objects.create(name='Лицей А', region=almaty, organization=org)
        results = api.get(SEARCH, {'search': 'лицей'}).data['results']
        assert [(s['name'], s['on_platform']) for s in results] == [('Лицей А', True), ('Лицей Б', False)]


@pytest.mark.django_db
class TestRegistrationWithSchool:
    def test_student_must_pick_or_add_school(self, api, org, settings):
        settings.DEFAULT_ORG_SLUG = org.slug
        res = register(api)
        assert res.status_code == 400
        assert 'school_id' in res.data['error']['details']

    def test_parent_may_skip_school(self, api, org, settings):
        settings.DEFAULT_ORG_SLUG = org.slug
        assert register(api, role='parent').status_code == 201

    def test_school_on_platform_puts_student_into_its_org(self, api, org, other_org, almaty, settings):
        settings.DEFAULT_ORG_SLUG = other_org.slug
        school = School.objects.create(name='ФМЛ', region=almaty, organization=org)
        assert register(api, school_id=school.id).status_code == 201
        user = User.objects.get(email='new@a.kz')
        assert user.school == school
        assert OrgMembership.objects.filter(user=user, org=org, role='student').exists()
        assert not OrgMembership.objects.filter(user=user, org=other_org).exists()

    def test_directory_school_off_platform_uses_default_org(self, api, org, almaty, settings):
        settings.DEFAULT_ORG_SLUG = org.slug
        school = School.objects.create(name='№ 8 школа', region=almaty)
        assert register(api, school_id=school.id).status_code == 201
        user = User.objects.get(email='new@a.kz')
        assert user.school == school and user.memberships.get().org == org

    def test_own_school_or_club_goes_to_moderation(self, api, org, astana, settings):
        settings.DEFAULT_ORG_SLUG = org.slug
        res = register(api, new_school={'name': '  Робототехника   үйірмесі ', 'kind': 'club',
                                        'region': astana.id, 'locality': 'Астана'})
        assert res.status_code == 201
        school = User.objects.get(email='new@a.kz').school
        assert (school.name, school.kind, school.is_approved, school.source) == \
            ('Робототехника үйірмесі', 'club', False, 'user')
        assert school.created_by.email == 'new@a.kz'
        assert res.data['user']['school']['is_approved'] is False
        # До одобрения в поиске не видна
        assert api.get(SEARCH, {'search': 'Робототехника'}).data['results'] == []

    def test_hidden_school_and_both_choices_rejected(self, api, org, almaty, settings):
        settings.DEFAULT_ORG_SLUG = org.slug
        hidden = School.objects.create(name='Закрыта', region=almaty, is_active=False)
        assert register(api, school_id=hidden.id).status_code == 400
        shown = School.objects.create(name='Открыта', region=almaty)
        both = register(api, school_id=shown.id, new_school={'name': 'Своя школа', 'region': almaty.id})
        assert both.status_code == 400


@pytest.mark.django_db
class TestImport:
    def test_kind_detection(self):
        assert detect_kind('Назарбаев Зияткерлік мектебі') == 'specialized'
        assert detect_kind('Гимназия № 159') == 'gymnasium'
        assert detect_kind('№ 39 лицейі') == 'lyceum'
        assert detect_kind('Балалар музыка мектебі') == 'extra'
        assert detect_kind('Средняя школа № 4') == 'school'
        assert detect_kind('Центральная казахская школа') == 'school'
        assert detect_kind('Школа-центр дополнительного образования № 29') == 'extra'
        assert detect_kind('Центр Лингво') == 'center'

    def test_osm_records_take_nearest_settlement_and_drop_junk(self):
        places = [
            {'type': 'node', 'id': 1, 'lat': 50.00, 'lon': 70.00, 'tags': {'place': 'village', 'name': 'Ақсу'}},
            {'type': 'node', 'id': 2, 'lat': 50.30, 'lon': 70.00, 'tags': {'place': 'town', 'name': 'Қарағай',
                                                                             'name:ru': 'Карагай'}},
        ]
        schools = [
            {'type': 'way', 'id': 10, 'center': {'lat': 50.01, 'lon': 70.01}, 'tags': {'name': '№ 1 мектеп'}},
            {'type': 'node', 'id': 11, 'lat': 50.31, 'lon': 70.0, 'tags': {'name': 'Гимназия № 2'}},
            {'type': 'node', 'id': 12, 'lat': 49.0, 'lon': 69.0, 'tags': {'name': 'Далёкая школа № 3'}},
            {'type': 'node', 'id': 13, 'lat': 50.0, 'lon': 70.0, 'tags': {'name': 'Административный корпус'}},
            {'type': 'node', 'id': 14, 'lat': 50.0, 'lon': 70.0, 'tags': {'name': 'Школа'}},
        ]
        records = build_records('KZ-35', schools, places)
        assert [(r['external_id'], r['locality']) for r in records] == [
            ('osm:way/10', 'Ақсу'), ('osm:node/11', 'Карагай'), ('osm:node/12', '')]
        city = build_records('KZ-75', schools[:1], [], city_name='Алматы')
        assert city[0]['locality'] == 'Алматы'

    def test_import_is_idempotent_dedupes_and_skips_driving_schools(self, almaty):
        records = [
            {'external_id': 'osm:way/1', 'name': '№ 4 орта мектебі', 'name_ru': 'Средняя школа №4',
             'region_code': 'KZ-75', 'locality': 'Алматы'},
            {'external_id': 'osm:node/2', 'name': '№ 4 орта мектебі', 'region_code': 'KZ-75', 'locality': 'Алматы'},
            {'external_id': 'osm:way/3', 'name': 'Автошкола Драйв', 'region_code': 'KZ-75'},
            {'external_id': 'osm:way/4', 'name': 'Без региона', 'region_code': 'KZ-00'},
        ]
        first = import_records(records)
        assert (first.created, first.skipped) == (1, 3)
        again = import_records(records)
        assert (again.created, again.updated) == (0, 1)
        school = School.objects.get()
        assert (school.name_ru, school.kind, school.is_approved) == ('Средняя школа №4', 'school', True)


@pytest.mark.django_db
class TestChangeOwnSchool:
    URL = '/api/v1/auth/users/me/school/'

    def test_pick_from_list_then_own_edits_same_pending_request(self, make_user, auth_client, org, almaty, astana):
        student = make_user('s@a.kz', 'student', org)
        client = auth_client(student, org.id)
        listed = School.objects.create(name='№ 8 школа', region=almaty)

        res = client.put(self.URL, {'school_id': listed.id}, format='json')
        assert res.status_code == 200 and res.data['school']['id'] == listed.id

        first = client.put(self.URL, {'new_school': {'name': 'Шахмат үйірмесі', 'kind': 'club', 'region': astana.id}},
                           format='json')
        own_id = first.data['school']['id']
        assert first.data['school']['is_approved'] is False
        second = client.put(self.URL, {'new_school': {'name': 'Шахмат үйірмесі «Ладья»', 'kind': 'club',
                                                      'region': astana.id}}, format='json')
        assert second.data['school']['id'] == own_id  # та же заявка, без дублей
        assert School.objects.get(id=own_id).name == 'Шахмат үйірмесі «Ладья»'
        assert School.objects.filter(source='user').count() == 1

    def test_clear_school_and_guest_forbidden(self, api, make_user, auth_client, org):
        student = make_user('s@a.kz', 'student', org)
        res = auth_client(student, org.id).put(self.URL, {'school_id': None}, format='json')
        assert res.status_code == 200 and res.data['school'] is None
        assert api.put(self.URL, {'school_id': None}, format='json').status_code == 401
