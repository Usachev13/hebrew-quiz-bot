#!/bin/bash
# Первоначальная настройка чистого сервера Ubuntu (22.04/24.04) под бота.
# Запускать на самом VPS от root (или через sudo), например через Termius.
#
# Использование:
#   ./setup_server.sh <git-repo-url>
#
# Пример:
#   ./setup_server.sh https://github.com/Usachev13/hebrew-quiz-bot.git
#
# Что делает:
# 1. Обновляет систему, ставит Python/venv/git.
# 2. Ставит Caddy (веб-сервер с автоматическим HTTPS через Let's Encrypt).
# 3. Создаёт отдельного системного пользователя botuser (без логина) —
#    бот не должен работать от root.
# 4. Клонирует репозиторий в /opt/hebrew-quiz-bot и ставит зависимости
#    в виртуальное окружение.
#
# После этого скрипта:
# - вручную создать /opt/hebrew-quiz-bot/.env с TELEGRAM_TOKEN (см. .env.example)
# - запустить deploy/install_service.sh <домен>

set -e

REPO_URL="$1"
APP_DIR="/opt/hebrew-quiz-bot"

if [ -z "$REPO_URL" ]; then
    echo "Использование: $0 <git-repo-url>"
    exit 1
fi

echo "== Обновление системы =="
apt update && apt -y upgrade

echo "== Базовые пакеты =="
apt install -y python3 python3-venv python3-pip git curl debian-keyring debian-archive-keyring apt-transport-https gnupg

echo "== Установка Caddy (авто-HTTPS) =="
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy

echo "== Системный пользователь botuser =="
# --no-create-home специально: если создать домашнюю папку заранее, в ней
# появятся системные dotfile-заготовки (.bashrc и т.п.), и git clone потом
# откажется клонировать в "непустую" директорию. Пусть папку создаст сам
# git clone ниже.
id -u botuser &>/dev/null || useradd --system --no-create-home --home "$APP_DIR" --shell /usr/sbin/nologin botuser

echo "== Клонирование репозитория =="
if [ -d "$APP_DIR/.git" ]; then
    echo "Репозиторий уже есть в $APP_DIR, пропускаю clone (используй git pull)."
else
    git clone "$REPO_URL" "$APP_DIR"
fi
chown -R botuser:botuser "$APP_DIR"

echo "== Виртуальное окружение и зависимости =="
sudo -u botuser python3 -m venv "$APP_DIR/venv"
sudo -u botuser "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u botuser "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo
echo "Готово. Дальше:"
echo "1. sudo -u botuser nano $APP_DIR/.env   # впиши TELEGRAM_TOKEN=..."
echo "2. ./deploy/install_service.sh <твой-домен>   # например ivrit-trainer.duckdns.org"
