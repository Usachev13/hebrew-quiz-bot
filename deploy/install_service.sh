#!/bin/bash
# Второй шаг после setup_server.sh: разворачивает systemd-сервис для бота
# (gunicorn) и настраивает Caddy на автоматический HTTPS для указанного
# домена. Запускать от root/sudo.
#
# Использование:
#   ./install_service.sh <домен>
#
# Пример:
#   ./install_service.sh ivrit-trainer.duckdns.org
#
# Перед запуском убедись, что:
# - домен уже указывает (A-запись) на IP этого сервера;
# - /opt/hebrew-quiz-bot/.env создан и содержит TELEGRAM_TOKEN.

set -e

DOMAIN="$1"
APP_DIR="/opt/hebrew-quiz-bot"

if [ -z "$DOMAIN" ]; then
    echo "Использование: $0 <домен>"
    exit 1
fi

if [ ! -f "$APP_DIR/.env" ]; then
    echo "Ошибка: $APP_DIR/.env не найден. Сначала создай его с TELEGRAM_TOKEN."
    exit 1
fi

echo "== systemd-юнит =="
cat > /etc/systemd/system/hebrew-quiz-bot.service <<EOF
[Unit]
Description=Hebrew Quiz Telegram Bot (Flask via gunicorn)
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
# --workers 1 обязательно: сессии игр (sessions = {}) хранятся в памяти
# процесса. Больше одного воркера — запросы от одного пользователя будут
# случайно попадать в разные процессы без общей памяти, и бот будет молча
# "зависать" через пару ответов (сессия не найдена в другом воркере).
#
# Параллельность даём потоками, а не процессами: потоки живут в одной
# памяти, поэтому sessions остаётся общим и корректным, но несколько
# пользователей обслуживаются одновременно (каждый запрос почти всё время
# ждёт ответа Telegram API, так что потоки тут эффективны).
#
# Когда пользователей станет много — выносить sessions в Redis/БД и
# только тогда поднимать --workers.
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 1 --threads 8 --bind 127.0.0.1:8000 bot:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hebrew-quiz-bot
systemctl restart hebrew-quiz-bot

echo "== Таймер «слова дня» (каждое утро) =="
cat > /etc/systemd/system/hebrew-daily-word.service <<EOF
[Unit]
Description=Hebrew bot: рассылка слова дня
After=network.target

[Service]
Type=oneshot
User=botuser
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/python3 send_daily.py
EOF

# 08:00 по времени сервера. Часовой пояс задаётся в юните таймера ниже.
cat > /etc/systemd/system/hebrew-daily-word.timer <<EOF
[Unit]
Description=Hebrew bot: слово дня каждое утро

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Сервер в UTC, а аудитория в Израиле — переводим системное время,
# чтобы 08:00 в таймере означало утро по Израилю.
timedatectl set-timezone Asia/Jerusalem || true

systemctl daemon-reload
systemctl enable --now hebrew-daily-word.timer

echo "== Caddy (обратный прокси + авто-HTTPS для $DOMAIN) =="
cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    reverse_proxy 127.0.0.1:8000
}
EOF

systemctl reload caddy || systemctl restart caddy

echo
echo "Готово. Проверка:"
echo "  systemctl status hebrew-quiz-bot   # должен быть active (running)"
echo "  curl -I https://$DOMAIN/           # должен ответить 200"
echo
echo "Дальше пропиши вебхук на новый адрес (см. set_webhook.py) и обнови URL в нём на:"
echo "  https://$DOMAIN/webhook/<TELEGRAM_TOKEN>"
