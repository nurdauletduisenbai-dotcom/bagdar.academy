#!/usr/bin/env bash
# Обновить окружение до свежей версии из GitHub (от пользователя nur, без sudo):
#   bash ~/apps/backend-bagdar.academy/edu_platform/deploy/deploy.sh        # prod: bagdar.academy, ветка main
#   bash ~/apps/backend-bagdar.academy/edu_platform/deploy/deploy.sh dev    # dev: dev.bagdar.academy, ветка develop
# Из GitHub Actions вызывается через ci-deploy.sh после зелёного CI.
set -euo pipefail

# shellcheck source=environments.sh
. "$(dirname "$0")/environments.sh"
load_env "${1:-prod}"
export DJANGO_SETTINGS_MODULE=config.settings.prod
# pip иногда зависает на оборванном соединении с PyPI — без таймаута деплой висит бесконечно
export PIP_DEFAULT_TIMEOUT=30

step() { printf '\n\033[1;34m→ [%s] %s\033[0m\n' "$ENV_NAME" "$*"; }

if [ -z "${BAGDAR_DEPLOY_PULLED:-}" ]; then
    # Один деплой за раз: на 1 ГБ RAM две параллельные сборки фронтенда не помещаются
    exec 9>/tmp/bagdar-deploy.lock
    flock 9

    step "Код: $BRANCH"
    cd "$REPO_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull --ff-only origin "$BRANCH"
    git log --oneline -1

    # Остальные шаги — из только что обновлённой ветки окружения: в develop они могут быть новее,
    # чем в скрипте, который запустили (CI всегда вызывает deploy.sh из prod-клона). Блокировка (fd 9) наследуется.
    BAGDAR_DEPLOY_PULLED=1 exec bash "$REPO_DIR/edu_platform/deploy/deploy.sh" "$ENV_NAME"
fi
cd "$REPO_DIR"

step "Python-зависимости"
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r edu_platform/backend/requirements.txt

step "Фронтенд: сборка"
cd "$REPO_DIR/edu_platform/frontend"
npm ci --no-audit --no-fund
npm run build
rsync -a --delete dist/ "$WEB_ROOT/frontend/"

step "Миграции и статика"
cd "$REPO_DIR/edu_platform/backend"
"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py import_schools --if-empty
"$VENV/bin/python" manage.py collectstatic --noinput -v 0
"$VENV/bin/python" manage.py check --deploy --fail-level ERROR

step "Перезапуск сервисов"
# shellcheck disable=SC2086
sudo /usr/bin/systemctl restart $SERVICES

step "Проверка"
for _ in $(seq 1 30); do
    if curl -fsS -H "Host: $DOMAIN" -H 'X-Forwarded-Proto: https' "http://127.0.0.1:$PORT/ready/"; then
        printf '\n\033[1;32m✓ %s: %s\033[0m\n' "$DOMAIN" "$(git -C "$REPO_DIR" log --oneline -1)"
        exit 0
    fi
    sleep 1
done
echo "✗ $DOMAIN: бэкенд не ответил. Логи: journalctl -u $SVC-backend -n 50" >&2
exit 1
