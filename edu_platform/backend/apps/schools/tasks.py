import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.news.tasks import leads_notify_configured, send_telegram

from .models import SchoolApplication

logger = logging.getLogger(__name__)

# Те же каналы, что и для заявок с главной (LEADS_TELEGRAM_*, LEADS_NOTIFY_EMAILS)
team_notify_configured = leads_notify_configured


def render_application(app: SchoolApplication) -> str:
    lines = [
        'Новая заявка на подключение школы',
        f'Школа: {app.school.name} ({app.school.locality or app.school.region})',
        f'Тип: {app.get_org_type_display()}',
        f'Заявитель: {app.contact_name}' + (f', {app.position}' if app.position else ''),
        f'Email: {app.email}',
        f'Телефон: {app.phone}',
    ]
    if app.students_count:
        lines.append(f'Учеников: ~{app.students_count}')
    if app.bin:
        lines.append(f'БИН: {app.bin}')
    if not app.school.is_approved:
        lines.append('Школы не было в справочнике — добавлена заявителем.')
    if app.is_claim:
        lines.append('⚠ У школы уже есть администратор — проверьте заявителя.')
    if app.message:
        lines.append(f'Комментарий: {app.message}')
    lines.append(f'Admin: {settings.FRONTEND_URL}/admin/schools/schoolapplication/{app.pk}/change/')
    return '\n'.join(lines)


@shared_task
def notify_new_school_application(application_id: int) -> None:
    app = SchoolApplication.objects.select_related('school__region').filter(pk=application_id).first()
    if not app or not team_notify_configured():
        return
    text = render_application(app)
    if settings.LEADS_TELEGRAM_BOT_TOKEN and settings.LEADS_TELEGRAM_CHAT_ID:
        try:
            send_telegram(text)
        except Exception as exc:  # noqa: BLE001 — каналы независимы, заявка уже сохранена
            logger.error('School application %s: Telegram notification failed: %s', application_id, exc)
    if settings.LEADS_NOTIFY_EMAILS:
        try:
            send_mail(f'Заявка школы: {app.school.name}', text, settings.DEFAULT_FROM_EMAIL,
                      settings.LEADS_NOTIFY_EMAILS, fail_silently=False)
        except Exception as exc:  # noqa: BLE001
            logger.error('School application %s: email notification failed: %s', application_id, exc)
