# Сервер bagdar.academy

VPS на Ubuntu 24.04 (`109.248.198.199`, вход `root`, приложение работает от пользователя `nur`). Всё работает без Docker:

```text
nginx :80/:443 ─┬─ /            → /var/www/bagdar.academy/frontend   (собранный Vue)
                ├─ /static/     → /var/www/bagdar.academy/static     (collectstatic)
                └─ /api /admin /docs /health … → gunicorn 127.0.0.1:8000  (bagdar-backend)
Celery: bagdar-worker + bagdar-beat → Redis 127.0.0.1:6379
PostgreSQL 127.0.0.1:5432, база bagdar, роль bagdar
```

| Что | Где |
|---|---|
| Клон репозитория | `/home/nur/apps/backend-bagdar.academy` (ветка `main`) |
| Python venv | `/home/nur/apps/backend-bagdar.academy/venv` |
| Секреты (`.env`) | `/home/nur/apps/backend-bagdar.academy/edu_platform/.env`, шаблон — [env.prod.example](env.prod.example) |
| Загруженные файлы | `/var/lib/bagdar/media` |
| Юниты systemd | [systemd/](systemd/) → `/etc/systemd/system/` |
| nginx | [nginx/](nginx/) → `/etc/nginx/sites-available/bagdar.academy` + `snippets/bagdar-locations.conf` |

## Первая настройка (один раз)

На чистом сервере от root:

```bash
id nur || useradd --create-home --shell /bin/bash nur
sudo -u nur git clone https://github.com/nurdauletduisenbai-dotcom/backend-bagdar.academy.git /home/nur/apps/backend-bagdar.academy
bash /home/nur/apps/backend-bagdar.academy/edu_platform/deploy/setup.sh
```

Скрипт ставит nginx, PostgreSQL, Redis, Node.js 22 и certbot (и swap, если RAM меньше 2 ГБ), создаёт роль и базу PostgreSQL, генерирует `.env` с секретами,
ставит юниты systemd и сайт nginx, затем делает первый деплой. Повторный запуск безопасен.

Затем HTTPS — когда A-записи `bagdar.academy` и `www` указывают на сервер:

```bash
sudo bash edu_platform/deploy/setup.sh ssl
```

## Обновление (после релиза в `main`)

```bash
bash ~/apps/backend-bagdar.academy/edu_platform/deploy/deploy.sh
```

`git pull` → зависимости → сборка фронтенда → миграции → `collectstatic` → перезапуск сервисов → проверка `/ready/`.

## Диагностика

```bash
systemctl status bagdar-backend bagdar-worker bagdar-beat
journalctl -u bagdar-backend -f
sudo nginx -t && sudo tail -f /var/log/nginx/error.log
```
