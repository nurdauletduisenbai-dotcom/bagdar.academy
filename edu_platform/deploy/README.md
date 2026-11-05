# Сервер bagdar.academy

VPS на Ubuntu 24.04 (`109.248.198.199`, вход `root`, приложение работает от пользователя `nur`). Всё работает без Docker.
На сервере два окружения, настройки каждого — в [environments.sh](environments.sh):

| | prod | dev |
|---|---|---|
| Адрес | https://bagdar.academy (+ `www`) | https://dev.bagdar.academy |
| Ветка | `main` | `develop` |
| Клон и venv | `/home/nur/apps/backend-bagdar.academy` | `/home/nur/apps/bagdar-dev` |
| gunicorn | `127.0.0.1:8000`, 2 воркера | `127.0.0.1:8001`, 1 воркер |
| systemd | `bagdar-backend`, `bagdar-worker`, `bagdar-beat` | `bagdar-dev-backend`, `bagdar-dev-worker`, `bagdar-dev-beat` |
| PostgreSQL | база и роль `bagdar` | база и роль `bagdar_dev` |
| Redis | базы 0–2 | базы 3–5 |
| Фронтенд и статика | `/var/www/bagdar.academy/` | `/var/www/dev.bagdar.academy/` |
| Загруженные файлы | `/var/lib/bagdar/media` | `/var/lib/bagdar-dev/media` |

```text
nginx :80/:443 ─┬─ /            → /var/www/<домен>/frontend   (собранный Vue)
                ├─ /static/     → /var/www/<домен>/static     (collectstatic)
                └─ /api /admin /docs /health /sitemap.xml … → gunicorn (bagdar[-dev]-backend)
Celery: bagdar[-dev]-worker + bagdar[-dev]-beat → Redis 127.0.0.1:6379
```

Секреты окружения — `<клон>/edu_platform/.env` (chmod 600, шаблон — [env.prod.example](env.prod.example)).
Юниты systemd и nginx-snippet собираются из шаблонов [systemd/*.in](systemd/) и [nginx/locations.conf.in](nginx/locations.conf.in).

## Автодеплой (GitHub Actions)

[`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml): после зелёного CI на push в `main` обновляется
bagdar.academy, в `develop` — dev.bagdar.academy. Вручную: Actions → Deploy → Run workflow.

Workflow заходит на сервер ключом из секрета `DEPLOY_SSH_KEY`. В `authorized_keys` этот ключ привязан к
[ci-deploy.sh](ci-deploy.sh), поэтому им можно только запустить деплой `prod` или `dev`. Ключ создаётся один раз:

```bash
bash /home/nur/apps/backend-bagdar.academy/edu_platform/deploy/setup.sh ci-key
```

Скрипт печатает приватный ключ. Добавьте его в GitHub: **Settings → Secrets and variables → Actions →
New repository secret**, Name `DEPLOY_SSH_KEY`.

## Первая настройка (один раз, от root)

На чистом сервере:

```bash
id nur || useradd --create-home --shell /bin/bash nur
sudo -u nur git clone https://github.com/nurdauletduisenbai-dotcom/bagdar.academy.git /home/nur/apps/backend-bagdar.academy
bash /home/nur/apps/backend-bagdar.academy/edu_platform/deploy/setup.sh          # prod
bash /home/nur/apps/backend-bagdar.academy/edu_platform/deploy/setup.sh ssl      # HTTPS для prod
```

Скрипт ставит nginx, PostgreSQL, Redis, Node.js 22 и certbot (и swap, если RAM меньше 2 ГБ), создаёт роль и базу,
генерирует `.env` с секретами, ставит юниты systemd и сайт nginx, затем делает первый деплой. Повторный запуск безопасен.

Dev — когда A-запись `dev.bagdar.academy` указывает на сервер:

```bash
bash /home/nur/apps/backend-bagdar.academy/edu_platform/deploy/setup.sh dev      # клон develop, база, .env, сервисы
bash /home/nur/apps/backend-bagdar.academy/edu_platform/deploy/setup.sh dev ssl  # HTTPS для dev
```

## Обновление вручную

```bash
sudo -u nur -H bash /home/nur/apps/backend-bagdar.academy/edu_platform/deploy/deploy.sh       # prod
sudo -u nur -H bash /home/nur/apps/backend-bagdar.academy/edu_platform/deploy/deploy.sh dev   # dev
```

`git pull` → зависимости → сборка фронтенда → миграции → `collectstatic` → перезапуск сервисов → проверка `/ready/`.
Деплои идут по очереди (`flock`): две сборки фронтенда одновременно в 1 ГБ RAM не помещаются.

## Диагностика

```bash
systemctl status bagdar-backend bagdar-worker bagdar-beat          # dev: bagdar-dev-*
journalctl -u bagdar-backend -f
nginx -t && tail -f /var/log/nginx/error.log
```
