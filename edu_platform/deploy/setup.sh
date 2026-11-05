#!/usr/bin/env bash
# Первичная настройка сервера bagdar.academy (Ubuntu 24.04 / Debian 12+, можно на чистом сервере).
# Запускать с sudo из клона репозитория:
#   sudo bash ~/apps/backend-bagdar.academy/edu_platform/deploy/setup.sh        # пакеты, БД, .env, systemd, nginx, первый деплой
#   sudo bash ~/apps/backend-bagdar.academy/edu_platform/deploy/setup.sh ssl    # HTTPS-сертификат (когда домен смотрит на сервер)
# Скрипт можно запускать повторно: существующие .env, роль и база не пересоздаются.
set -euo pipefail

APP_USER=nur
DOMAIN=bagdar.academy
REPO_DIR=/home/$APP_USER/apps/backend-bagdar.academy
DEPLOY_DIR="$REPO_DIR/edu_platform/deploy"
ENV_FILE="$REPO_DIR/edu_platform/.env"
WEB_ROOT=/var/www/$DOMAIN
DB_NAME="${DB_NAME:-bagdar}"
DB_USER="${DB_USER:-bagdar}"
BRANCH="${BRANCH:-main}"

step() { printf '\n\033[1;34m→ %s\033[0m\n' "$*"; }
[ "$(id -u)" = 0 ] || { echo "Запустите через sudo" >&2; exit 1; }

install_nginx_site() {
    install -m 644 "$DEPLOY_DIR/nginx/bagdar-locations.conf" /etc/nginx/snippets/bagdar-locations.conf
    install -m 644 "$DEPLOY_DIR/nginx/$DOMAIN.$1.conf" /etc/nginx/sites-available/$DOMAIN
    ln -sfn /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN
    rm -f /etc/nginx/sites-enabled/default   # сам файл остаётся в sites-available
    nginx -t
    systemctl reload nginx
}

if [ "${1:-}" = ssl ]; then
    step "Сертификат Let's Encrypt для $DOMAIN и www.$DOMAIN"
    certbot certonly --webroot -w /var/www/letsencrypt -d "$DOMAIN" -d "www.$DOMAIN" \
        --non-interactive --agree-tos --register-unsafely-without-email --keep-until-expiring
    printf '#!/bin/sh\nsystemctl reload nginx\n' > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
    chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
    install_nginx_site https
    sed -i 's/^DJANGO_SECURE_SSL_REDIRECT=.*/DJANGO_SECURE_SSL_REDIRECT=True/' "$ENV_FILE"
    systemctl restart bagdar-backend bagdar-worker bagdar-beat
    echo "✓ https://$DOMAIN"
    exit 0
fi

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

step "Каталоги"
install -d -o "$APP_USER" -g "$APP_USER" "$WEB_ROOT" "$WEB_ROOT/frontend" "$WEB_ROOT/static" /var/lib/bagdar /var/lib/bagdar/media
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
        "$DEPLOY_DIR/env.prod.example" > "$ENV_FILE"
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    chmod 600 "$ENV_FILE"
else
    echo "$ENV_FILE уже есть — роль, база и секреты не трогаю"
fi

step "systemd: bagdar-backend, bagdar-worker, bagdar-beat"
if [ -f /etc/systemd/system/myproject.service ]; then   # старый юнит, указывал на несуществующий venv
    systemctl disable --now myproject.service || true
    mv /etc/systemd/system/myproject.service /etc/systemd/system/myproject.service.disabled
fi
install -m 644 "$DEPLOY_DIR"/systemd/bagdar-*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable bagdar-backend bagdar-worker bagdar-beat

step "sudo без пароля только для перезапуска сервисов (нужно deploy.sh)"
cat > /etc/sudoers.d/bagdar-deploy <<EOF
$APP_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart bagdar-backend bagdar-worker bagdar-beat
EOF
chmod 440 /etc/sudoers.d/bagdar-deploy
visudo -cf /etc/sudoers.d/bagdar-deploy

step "nginx (пока по HTTP)"
if [ -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem ]; then install_nginx_site https; else install_nginx_site http; fi

step "Первый деплой ветки $BRANCH"
sudo -u "$APP_USER" -H bash "$DEPLOY_DIR/deploy.sh" "$BRANCH"

echo
echo "✓ Сайт работает по http://$DOMAIN"
echo "  HTTPS (когда DNS домена указывает на этот сервер):"
echo "  sudo bash $DEPLOY_DIR/setup.sh ssl"
