# Окружения на сервере (подключается из setup.sh, deploy.sh, ci-deploy.sh):
#   prod — https://bagdar.academy      ветка main     /home/nur/apps/backend-bagdar.academy  :8000
#   dev  — https://dev.bagdar.academy  ветка develop  /home/nur/apps/bagdar-dev              :8001
# Каждое окружение — свой клон, venv, .env, база, Redis-базы, юниты systemd и сайт nginx.

APP_USER=nur
REPO_URL=https://github.com/nurdauletduisenbai-dotcom/bagdar.academy.git

load_env() {
    case "${1:-prod}" in
        prod|main)
            ENV_NAME=prod BRANCH=main DOMAIN=bagdar.academy
            REPO_DIR=/home/$APP_USER/apps/backend-bagdar.academy
            PORT=8000 WORKERS=2 SVC=bagdar DB_NAME=bagdar DB_USER=bagdar REDIS_DB=0
            ;;
        dev|develop)
            ENV_NAME=dev BRANCH=develop DOMAIN=dev.bagdar.academy
            REPO_DIR=/home/$APP_USER/apps/bagdar-dev
            PORT=8001 WORKERS=1 SVC=bagdar-dev DB_NAME=bagdar_dev DB_USER=bagdar_dev REDIS_DB=3
            ;;
        *)
            echo "Неизвестное окружение '$1': нужно prod или dev" >&2
            return 1
            ;;
    esac
    VENV="$REPO_DIR/venv"
    ENV_FILE="$REPO_DIR/edu_platform/.env"
    WEB_ROOT=/var/www/$DOMAIN
    STATE_DIR=/var/lib/$SVC
    SERVICES="$SVC-backend $SVC-worker $SVC-beat"
}
