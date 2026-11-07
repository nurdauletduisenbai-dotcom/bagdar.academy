import json
import logging
import urllib.request

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import ContactRequest

logger = logging.getLogger(__name__)

TELEGRAM_API = 'https://api.telegram.org/bot{token}/sendMessage'
TELEGRAM_TIMEOUT = 10


def leads_notify_configured() -> bool:
    telegram = settings.LEADS_TELEGRAM_BOT_TOKEN and settings.LEADS_TELEGRAM_CHAT_ID
    return bool(telegram or settings.LEADS_NOTIFY_EMAILS)


def render_lead(req: ContactRequest) -> str:
    lines = [
        'Новая заявка с сайта bagdar.academy',
        f'Имя: {req.name}',
        f'Телефон: {req.phone}',
        f'Кто: {req.get_audience_display()}',
    ]
    if req.language:
        lines.append(f'Язык сайта: {req.language}')
    if req.message:
        lines.append(f'Вопрос: {req.message}')
    lines.append(f'Admin: {settings.FRONTEND_URL}/admin/news/contactrequest/{req.pk}/change/')
    return '\n'.join(lines)


def send_telegram(text: str) -> None:
    data = json.dumps({
        'chat_id': settings.LEADS_TELEGRAM_CHAT_ID,
        'text': text,
        'disable_web_page_preview': True,
    }).encode()
    request = urllib.request.Request(
        TELEGRAM_API.format(token=settings.LEADS_TELEGRAM_BOT_TOKEN),
        data=data, headers={'Content-Type': 'application/json'}, method='POST',
    )
    with urllib.request.urlopen(request, timeout=TELEGRAM_TIMEOUT) as response:
        if response.status != 200:
            raise RuntimeError(f'Telegram API ответил {response.status}')


@shared_task
def notify_new_contact_request(request_id: int) -> None:
    """Сообщает команде о новой заявке. Каналы независимы: сбой одного не мешает другому и не роняет задачу."""
    req = ContactRequest.objects.filter(pk=request_id).first()
    if not req or not leads_notify_configured():
        return
    text = render_lead(req)

    if settings.LEADS_TELEGRAM_BOT_TOKEN and settings.LEADS_TELEGRAM_CHAT_ID:
        try:
            send_telegram(text)
        except Exception as exc:  # noqa: BLE001 — сеть/Telegram недоступны: заявка уже сохранена
            logger.error('Lead %s: Telegram notification failed: %s', request_id, exc)

    if settings.LEADS_NOTIFY_EMAILS:
        try:
            send_mail(
                subject=f'Заявка с сайта: {req.name}, {req.phone}',
                message=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=settings.LEADS_NOTIFY_EMAILS,
                fail_silently=False,
            )
        except Exception as exc:  # noqa: BLE001 — SMTP недоступен: заявка уже сохранена
            logger.error('Lead %s: email notification failed: %s', request_id, exc)
