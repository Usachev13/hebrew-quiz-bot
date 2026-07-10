#!/bin/bash
# Обновляет бота на PythonAnywhere одной командой: git pull + reload
# веб-приложения через PythonAnywhere API (без захода в веб-интерфейс).
#
# Разовая настройка:
# 1. На pythonanywhere.com: Account -> вкладка API Token -> Create a new
#    API token (если ещё не создан).
# 2. Добавь в .env рядом с этим скриптом строку:
#      PA_API_TOKEN=твой_api_токен
# 3. chmod +x deploy.sh (один раз, чтобы можно было запускать напрямую).
#
# Дальше просто: ./deploy.sh

set -e

cd "$(dirname "$0")"

PA_USERNAME="Usachev13"
PA_DOMAIN="usachev13.pythonanywhere.com"

if [ -f .env ]; then
    # подтягиваем PA_API_TOKEN из .env, не трогая остальные переменные
    export "$(grep -E '^PA_API_TOKEN=' .env | xargs)"
fi

if [ -z "$PA_API_TOKEN" ]; then
    echo "Ошибка: PA_API_TOKEN не найден."
    echo "Добавь строку PA_API_TOKEN=твой_токен в .env (см. комментарий в начале файла)."
    exit 1
fi

echo "== git pull =="
git pull

echo "== Reload $PA_DOMAIN =="
curl -s -X POST \
    -H "Authorization: Token $PA_API_TOKEN" \
    "https://www.pythonanywhere.com/api/v0/user/$PA_USERNAME/webapps/$PA_DOMAIN/reload/"

echo
echo "Готово."
