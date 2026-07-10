#!/bin/bash
# Обновление бота на VPS одной командой: git pull + переустановка
# зависимостей (если изменились) + перезапуск systemd-сервиса.
# Запускать от root/sudo на самом сервере.
#
# Использование: ./update.sh

set -e

APP_DIR="/opt/hebrew-quiz-bot"
cd "$APP_DIR"

echo "== git pull =="
sudo -u botuser git pull

echo "== зависимости =="
sudo -u botuser "$APP_DIR/venv/bin/pip" install -r requirements.txt

echo "== перезапуск сервиса =="
systemctl restart hebrew-quiz-bot
systemctl status hebrew-quiz-bot --no-pager -l | head -10

echo "Готово."
