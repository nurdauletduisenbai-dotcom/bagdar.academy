#!/usr/bin/env bash
# Точка входа для GitHub Actions. Ключ деплоя в ~nur/.ssh/authorized_keys привязан к этому скрипту
# (command="…/ci-deploy.sh",restrict), поэтому по нему можно только запустить деплой prod или dev —
# никакой другой команды или shell. Окружение приходит как команда ssh: `ssh nur@сервер dev`.
set -euo pipefail

case "${SSH_ORIGINAL_COMMAND:-}" in
    prod|dev) exec bash "$(dirname "$0")/deploy.sh" "$SSH_ORIGINAL_COMMAND" ;;
    *) echo "Ожидается prod или dev, получено: '${SSH_ORIGINAL_COMMAND:-}'" >&2; exit 2 ;;
esac
