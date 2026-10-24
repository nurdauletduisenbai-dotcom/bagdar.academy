"""
Заявки на подключение школы: подача (публично) и рассмотрение суперпользователем.

Одобрение за одну транзакцию: школа одобряется в справочнике, берётся/создаётся её организация
(ученики, выбравшие школу раньше, уже там), заявитель становится администратором —
сразу, если аккаунт с этим email есть, иначе по одноразовому приглашению на email (7 дней).
"""
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.organizations.models import Invite, OrgMembership

from .models import School, SchoolApplication
from .services import ensure_organization

logger = logging.getLogger(__name__)
INVITE_DAYS = 7

# ---------- Тексты писем (язык — тот, на котором заявитель смотрел сайт) ----------
MAILS = {
    'ru': {
        'approved_subject': 'bagdar.academy: заявка школы одобрена',
        'approved_member': ('Здравствуйте, {name}!\n\nЗаявка на подключение «{school}» к bagdar.academy одобрена. '
                            'Вы — администратор школы.\n\nВойдите: {site}/login и выберите организацию «{org}» '
                            'в меню профиля. Дальше вы сможете приглашать учителей и учеников и создавать курсы.'),
        'approved_invite': ('Здравствуйте, {name}!\n\nЗаявка на подключение «{school}» к bagdar.academy одобрена.\n\n'
                            'Создайте аккаунт по ссылке (действует {days} дней):\n{link}\n\n'
                            'После регистрации вы станете администратором школы: сможете приглашать учителей и '
                            'учеников и создавать курсы.'),
        'rejected_subject': 'bagdar.academy: заявка школы не одобрена',
        'rejected': ('Здравствуйте, {name}!\n\nК сожалению, заявка на подключение «{school}» не одобрена.\n'
                     'Причина: {note}\n\nЕсли это ошибка — ответьте на это письмо или отправьте заявку снова.'),
        'rejected_default': 'не удалось подтвердить, что вы представляете эту школу.',
        'info_subject': 'bagdar.academy: уточните данные заявки',
        'info': ('Здравствуйте, {name}!\n\nЧтобы рассмотреть заявку на подключение «{school}», нам нужно уточнить:\n'
                 '{note}\n\nОтветьте, пожалуйста, на это письмо.'),
    },
    'kk': {
        'approved_subject': 'bagdar.academy: мектеп өтінімі мақұлданды',
        'approved_member': ('Сәлеметсіз бе, {name}!\n\n«{school}» мектебін bagdar.academy платформасына қосу туралы '
                            'өтінім мақұлданды. Сіз мектеп әкімшісісіз.\n\nКіріңіз: {site}/login және профиль '
                            'мәзірінен «{org}» ұйымын таңдаңыз. Содан кейін мұғалімдер мен оқушыларды шақырып, '
                            'курстар құра аласыз.'),
        'approved_invite': ('Сәлеметсіз бе, {name}!\n\n«{school}» мектебін bagdar.academy платформасына қосу туралы '
                            'өтінім мақұлданды.\n\nАккаунтты мына сілтеме арқылы ашыңыз ({days} күн жарамды):\n'
                            '{link}\n\nТіркелгеннен кейін сіз мектеп әкімшісі боласыз: мұғалімдер мен оқушыларды '
                            'шақырып, курстар құра аласыз.'),
        'rejected_subject': 'bagdar.academy: мектеп өтінімі мақұлданбады',
        'rejected': ('Сәлеметсіз бе, {name}!\n\nӨкінішке қарай, «{school}» мектебін қосу туралы өтінім '
                     'мақұлданбады.\nСебебі: {note}\n\nЕгер бұл қате болса, осы хатқа жауап беріңіз немесе '
                     'өтінімді қайта жіберіңіз.'),
        'rejected_default': 'сіздің осы мектептің өкілі екеніңізді растай алмадық.',
        'info_subject': 'bagdar.academy: өтінім деректерін нақтылаңыз',
        'info': ('Сәлеметсіз бе, {name}!\n\n«{school}» мектебін қосу туралы өтінімді қарау үшін мынаны нақтылау '
                 'қажет:\n{note}\n\nОсы хатқа жауап беріңіз.'),
    },
}


def _texts(app: SchoolApplication) -> dict:
    return MAILS['kk' if app.language == 'kk' else 'ru']


def _send(app: SchoolApplication, subject: str, body: str) -> None:
    def send():
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [app.email], fail_silently=False)
        except Exception as exc:  # noqa: BLE001 — решение уже сохранено; письмо можно отправить повторно
            logger.error('School application %s: email to applicant failed: %s', app.pk, exc)
    transaction.on_commit(send)


def school_has_admin(school: School) -> bool:
    return bool(school.organization_id) and OrgMembership.objects.filter(
        org_id=school.organization_id, role='admin', is_active=True).exists()


# ---------- Подача ----------

@transaction.atomic
def submit(data: dict) -> SchoolApplication:
    school = data.pop('school', None)
    new_school = data.pop('new_school', None)
    if new_school:
        school = School.objects.create(**new_school, is_approved=False, source=School.Source.USER)
    elif SchoolApplication.objects.filter(school=school, email__iexact=data['email'],
                                          status__in=[SchoolApplication.Status.NEW,
                                                      SchoolApplication.Status.NEEDS_INFO]).exists():
        raise ValidationError({'email': 'Заявка от этого email на эту школу уже на рассмотрении.'})
    app = SchoolApplication.objects.create(school=school, is_claim=school_has_admin(school), **data)

    from .tasks import notify_new_school_application, team_notify_configured
    if team_notify_configured():
        def queue():
            try:
                notify_new_school_application.delay(app.pk)
            except Exception as exc:  # noqa: BLE001 — брокер недоступен: заявка уже сохранена
                logger.error('School application %s: failed to queue team notification: %s', app.pk, exc)
        transaction.on_commit(queue)
    return app


# ---------- Рассмотрение ----------

@transaction.atomic
def approve(app: SchoolApplication, by) -> dict:
    """Возвращает {'invited': bool, 'org': Organization}. Повторно одобрить нельзя."""
    app = SchoolApplication.objects.select_for_update().select_related('school').get(pk=app.pk)
    if app.status == SchoolApplication.Status.APPROVED:
        raise ValidationError('Заявка уже одобрена.')
    school = app.school
    if not (school.is_approved and school.is_active):
        school.is_approved = school.is_active = True
        school.save(update_fields=['is_approved', 'is_active', 'updated_at'])
    org = ensure_organization(school)

    texts = _texts(app)
    ctx = {'name': app.contact_name, 'school': school.name_ru or school.name, 'org': org.name,
           'site': settings.FRONTEND_URL, 'days': INVITE_DAYS}
    user = get_user_model().objects.filter(email__iexact=app.email, is_active=True).first()
    if user:
        membership, created = OrgMembership.objects.get_or_create(org=org, user=user, role='admin')
        if not created and not membership.is_active:
            membership.is_active = True
            membership.save(update_fields=['is_active', 'updated_at'])
        body = texts['approved_member'].format(**ctx)
    else:
        from apps.accounts.services import hash_token

        raw = secrets.token_urlsafe(32)
        Invite.objects.create(org=org, role='admin', max_uses=1, token_hash=hash_token(raw), created_by=by,
                              expires_at=timezone.now() + timedelta(days=INVITE_DAYS))
        body = texts['approved_invite'].format(**ctx, link=f'{settings.FRONTEND_URL}/invite?token={raw}')

    app.status = SchoolApplication.Status.APPROVED
    app.reviewed_by, app.reviewed_at = by, timezone.now()
    app.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
    _send(app, texts['approved_subject'], body)

    from apps.audit.services import AuditService
    AuditService.log(AuditService.Action.ROLE_CHANGE, user=by, org_id=org.id, entity=app,
                     changes={'school_application': app.pk, 'admin_email': app.email, 'invited': user is None})
    return {'invited': user is None, 'org': org}


@transaction.atomic
def reject(app: SchoolApplication, by) -> None:
    texts = _texts(app)
    app.status = SchoolApplication.Status.REJECTED
    app.reviewed_by, app.reviewed_at = by, timezone.now()
    app.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
    note = app.review_note.strip() or texts['rejected_default']
    _send(app, texts['rejected_subject'], texts['rejected'].format(
        name=app.contact_name, school=app.school.name, note=note))


@transaction.atomic
def request_info(app: SchoolApplication, by) -> None:
    if not app.review_note.strip():
        raise ValidationError('Напишите в поле «Ответ заявителю», что нужно уточнить.')
    app.status = SchoolApplication.Status.NEEDS_INFO
    app.reviewed_by, app.reviewed_at = by, timezone.now()
    app.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'updated_at'])
    texts = _texts(app)
    _send(app, texts['info_subject'], texts['info'].format(
        name=app.contact_name, school=app.school.name, note=app.review_note.strip()))
