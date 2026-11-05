#!/usr/bin/env bash
# Настройка сервера bagdar.academy (Ubuntu 24.04 / Debian 12+, можно на чистом сервере). От root, из prod-клона:
#   bash edu_platform/deploy/setup.sh            # prod: пакеты, БД, .env, systemd, nginx, первый деплой main
#   bash edu_platform/deploy/setup.sh ssl        # prod: HTTPS-сертификат для bagdar.academy и www
#   bash edu_platform/deploy/setup.sh dev        # dev:  то же для dev.bagdar.academy (ветка develop)
#   bash edu_platform/deploy/setup.sh dev ssl    # dev:  HTTPS-сертификат для dev.bagdar.academy
#   bash edu_platform/deploy/setup.sh ci-key     # SSH-ключ, которым GitHub Actions запускает деплой
# Скрипт можно запускать повторно: существующие .env, роли и базы не пересоздаются.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=environments.sh
. "$SCRIPT_DIR/environments.sh"

ENV_ARG=prod
case "${1:-}" in prod|dev) ENV_ARG=$1; shift ;; esac
ACTION="${1:-install}"
load_env "$ENV_ARG"

step() { printf '\n\033[1;34m→ [%s] %s\033[0m\n' "$ENV_NAME" "$*"; }
[ "$(id -u)" = 0 ] || { echo "Запустите от root (sudo)" >&2; exit 1; }

# Хосты окружения: prod отвечает и на www
if [ "$ENV_NAME" = prod ]; then HOSTS="$DOMAIN www.$DOMAIN"; else HOSTS="$DOMAIN"; fi
ORIGINS="$(for h in $HOSTS; do printf 'https://%s,' "$h"; done | sed 's/,$//')"

# Подставляет значения окружения в шаблон (*.in) и пишет результат в $2
render() {
    sed -e "s|@DOMAIN@|$DOMAIN|g" -e "s|@REPO_DIR@|$REPO_DIR|g" -e "s|@PORT@|$PORT|g" \
        -e "s|@WORKERS@|$WORKERS|g" -e "s|@SVC@|$SVC|g" "$1" > "$2"
    chmod 644 "$2"
}

install_nginx_site() {
    render "$SCRIPT_DIR/nginx/locations.conf.in" "/etc/nginx/snippets/$SVC-locations.conf"
    install -m 644 "$SCRIPT_DIR/nginx/$DOMAIN.$1.conf" "/etc/nginx/sites-available/$DOMAIN"
    ln -sfn "/etc/nginx/sites-available/$DOMAIN" "/etc/nginx/sites-enabled/$DOMAIN"
    rm -f /etc/nginx/sites-enabled/default   # сам файл остаётся в sites-available
    nginx -t
    systemctl reload nginx
}

case "$ACTION" in
ssl)
    step "Сертификат Let's Encrypt: $HOSTS"
    # shellcheck disable=SC2046
    certbot certonly --webroot -w /var/www/letsencrypt $(printf -- '-d %s ' $HOSTS) \
        --non-interactive --agree-tos --register-unsafely-without-email --keep-until-expiring
    printf '#!/bin/sh\nsystemctl reload nginx\n' > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
    chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
    install_nginx_site https
    sed -i 's/^DJANGO_SECURE_SSL_REDIRECT=.*/DJANGO_SECURE_SSL_REDIRECT=True/' "$ENV_FILE"
    # shellcheck disable=SC2086
    systemctl restart $SERVICES
    echo "✓ https://$DOMAIN"
    exit 0
    ;;

ci-key)
    KEY=/home/$APP_USER/.ssh/bagdar_ci
    AUTH=/home/$APP_USER/.ssh/authorized_keys
    install -d -m 700 -o "$APP_USER" -g "$APP_USER" "/home/$APP_USER/.ssh"
    [ -f "$KEY" ] || sudo -u "$APP_USER" ssh-keygen -q -t ed25519 -N "" -C "github-actions-deploy" -f "$KEY"
    if ! grep -qF "$(cut -d' ' -f2 "$KEY.pub")" "$AUTH" 2>/dev/null; then
        # Ключ умеет только одно: запустить ci-deploy.sh (prod или dev). Ни shell, ни проброса портов.
        echo "command=\"bash $SCRIPT_DIR/ci-deploy.sh\",restrict $(cat "$KEY.pub")" >> "$AUTH"
        chown "$APP_USER:$APP_USER" "$AUTH"
        chmod 600 "$AUTH"
    fi
    echo
    echo "Скопируйте приватный ключ ниже ЦЕЛИКОМ (вместе со строками BEGIN/END) в GitHub:"
    echo "  Settings → Secrets and variables → Actions → New repository secret → Name: DEPLOY_SSH_KEY"
    echo
    cat "$KEY"
    exit 0
    ;;

install) ;;
*) echo "Неизвестное действие '$ACTION'. Варианты: (пусто), ssl, ci-key" >&2; exit 1 ;;
esac

step "Пользователь $APP_USER"
id "$APP_USER" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$APP_USER"

# npm ci + vue-tsc не помещаются в 1 ГБ RAM — на маленьких VPS добавляем swap
if [ "$(awk '/MemTotal/{print $2}' /proc/meminfo)" -lt 2000000 ] && [ "$(swapon --noheadings | wc -l)" = 0 ]; then
    step "Swap 2 ГБ (RAM меньше 2 ГБ)"
    fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

step "Пакеты: nginx, PostgreSQL, Redis, certbot, сборка Python"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q nginx postgresql redis-server python3-venv python3-dev libpq-dev \
    rsync curl ca-certificates gnupg openssl certbot
systemctl enable --now nginx postgresql redis-server

# Vite 8 требует Node.js >= 20.19; в Ubuntu 24.04 из коробки 18 — ставим 22 LTS из репозитория NodeSource
if [ "$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)" -lt 20 ]; then
    step "Node.js 22 (NodeSource)"
    install -d -m 755 /etc/apt/keyrings
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/nodesource.gpg
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list
    apt-get update -q
    apt-get install -y -q nodejs
fi
node --version

step "Код: $REPO_DIR (ветка $BRANCH)"
if [ ! -d "$REPO_DIR/.git" ]; then
    install -d -o "$APP_USER" -g "$APP_USER" "$(dirname "$REPO_DIR")"
    sudo -u "$APP_USER" git clone -q -b "$BRANCH" "$REPO_URL" "$REPO_DIR"
fi

step "Каталоги"
install -d -o "$APP_USER" -g "$APP_USER" "$WEB_ROOT" "$WEB_ROOT/frontend" "$WEB_ROOT/static" "$STATE_DIR" "$STATE_DIR/media"
install -d /var/www/letsencrypt

step "PostgreSQL: роль $DB_USER и база $DB_NAME"
if [ ! -f "$ENV_FILE" ]; then
    DB_PASS="$(openssl rand -hex 24)"
    if sudo -u postgres psql -tAc "select 1 from pg_roles where rolname='$DB_USER'" | grep -q 1; then
        sudo -u postgres psql -qc "alter role \"$DB_USER\" with login password '$DB_PASS'"
    else
        sudo -u postgres psql -qc "create role \"$DB_USER\" with login password '$DB_PASS'"
    fi
    if sudo -u postgres psql -tAc "select 1 from pg_database where datname='$DB_NAME'" | grep -q 1; then
        sudo -u postgres psql -qc "alter database \"$DB_NAME\" owner to \"$DB_USER\""
    else
        sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"
    fi

    step "Создаю $ENV_FILE с новыми секретами"
    SECRET_KEY="$(openssl rand -base64 48 | tr -d '\n=+/')"
    FERNET_KEY="$(python3 -c 'import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')"
    sed -e "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=$SECRET_KEY|" \
        -e "s|^TWO_FACTOR_ENCRYPTION_KEY=.*|TWO_FACTOR_ENCRYPTION_KEY=$FERNET_KEY|" \
        -e "s|^DATABASE_URL=.*|DATABASE_URL=postgres://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME|" \
        -e "s|^DJANGO_ALLOWED_HOSTS=.*|DJANGO_ALLOWED_HOSTS=${HOSTS// /,},localhost,127.0.0.1|" \
        -e "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=$ORIGINS|" \
        -e "s|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=$ORIGINS|" \
        -e "s|^FRONTEND_URL=.*|FRONTEND_URL=https://$DOMAIN|" \
        -e "s|^DJANGO_STATIC_ROOT=.*|DJANGO_STATIC_ROOT=$WEB_ROOT/static|" \
        -e "s|^DJANGO_MEDIA_ROOT=.*|DJANGO_MEDIA_ROOT=$STATE_DIR/media|" \
        -e "s|^REDIS_URL=.*|REDIS_URL=redis://127.0.0.1:6379/$REDIS_DB|" \
        -e "s|^CELERY_BROKER_URL=.*|CELERY_BROKER_URL=redis://127.0.0.1:6379/$((REDIS_DB + 1))|" \
        -e "s|^CELERY_RESULT_BACKEND=.*|CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/$((REDIS_DB + 2))|" \
        "$SCRIPT_DIR/env.prod.example" > "$ENV_FILE"
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
else
    echo "$ENV_FILE уже есть — роль, база и секреты не трогаю"
fi

step "systemd: $SERVICES"
if [ -f /etc/systemd/system/myproject.service ]; then   # старый юнит, указывал на несуществующий venv
    systemctl disable --now myproject.service || true
    mv /etc/systemd/system/myproject.service /etc/systemd/system/myproject.service.disabled
fi
for unit in backend worker beat; do
    render "$SCRIPT_DIR/systemd/$unit.service.in" "/etc/systemd/system/$SVC-$unit.service"
done
systemctl daemon-reload
# shellcheck disable=SC2086
systemctl enable $SERVICES

step "sudo без пароля только для перезапуска сервисов (нужно deploy.sh)"
{
    for e in prod dev; do (load_env "$e" && echo "$APP_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart $SERVICES"); done
} > /etc/sudoers.d/bagdar-deploy
chmod 440 /etc/sudoers.d/bagdar-deploy
visudo -cf /etc/sudoers.d/bagdar-deploy

step "nginx"
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then install_nginx_site https; else install_nginx_site http; fi

step "Первый деплой ветки $BRANCH"
sudo -u "$APP_USER" -H bash "$SCRIPT_DIR/deploy.sh" "$ENV_NAME"

echo
echo "✓ Сайт работает по http://$DOMAIN"
echo "  HTTPS (когда DNS домена указывает на этот сервер):"
echo "  bash $SCRIPT_DIR/setup.sh $([ "$ENV_NAME" = dev ] && echo 'dev ')ssl"
