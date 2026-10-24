"""
Школа из справочника ↔ организация на платформе: у ученика они всегда совпадают.

Если у выбранной школы ещё нет организации (её никто не подключал, администратора нет),
она создаётся автоматически — пустая: без курсов и персонала. Когда школа подключится,
суперпользователь назначит ей администратора или свяжет с уже существующей организацией.
"""
from django.db import transaction

from apps.organizations.models import Organization, OrgMembership

from .models import School

STUDENT = OrgMembership.Role.STUDENT


@transaction.atomic
def ensure_organization(school: School) -> Organization:
    """
    Организация школы; создаётся при первом ученике. select_for_update — без дублей при гонке.
    Переданный объект school тоже получает organization (его потом сериализуют в ответ).
    """
    locked = School.objects.select_for_update().get(pk=school.pk)
    org = locked.organization
    if org is None:
        org = Organization.objects.create(
            name=(locked.name_ru or locked.name)[:255], slug=f'school-{locked.pk}', timezone='Asia/Almaty')
        locked.organization = org
        locked.save(update_fields=['organization', 'updated_at'])
    elif not org.is_active:
        org.is_active = True
        org.save(update_fields=['is_active', 'updated_at'])
    school.organization = org
    return org


@transaction.atomic
def set_student_school(user, school: School | None) -> Organization | None:
    """
    Записывает школу ученику и переводит его членство «ученик» в организацию этой школы.
    Членство в организации прежней школы отключается; приглашения в другие организации не трогаем.
    """
    previous = user.school
    user.school = school
    user.save(update_fields=['school', 'updated_at'])
    if previous and previous.organization_id and (not school or previous.organization_id != school.organization_id):
        OrgMembership.objects.filter(user=user, org_id=previous.organization_id, role=STUDENT).update(is_active=False)
    if not school:
        return None
    org = ensure_organization(school)
    membership, created = OrgMembership.objects.get_or_create(org=org, user=user, role=STUDENT)
    if not created and not membership.is_active:
        membership.is_active = True
        membership.save(update_fields=['is_active', 'updated_at'])
    return org


@transaction.atomic
def move_students(school: School, old_org_id: int | None, new_org: Organization | None) -> int:
    """Ученики школы переходят из прежней организации в новую (смена связи в админке, слияние дублей)."""
    if not new_org or old_org_id == new_org.id:
        return 0
    moved = 0
    for user in school.students.all():
        if old_org_id:
            OrgMembership.objects.filter(user=user, org_id=old_org_id, role=STUDENT).update(is_active=False)
        membership, created = OrgMembership.objects.get_or_create(org=new_org, user=user, role=STUDENT)
        if not created and not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=['is_active', 'updated_at'])
        moved += 1
    return moved
