# Деплой на VPS (Hetzner + бесплатный домен DuckDNS + Caddy)

Пошаговый план. Шаги 1–2 делаешь руками в браузере (оплата и доменные
сервисы — это не то, что можно доверить скрипту). Дальше — SSH и три
готовых скрипта.

## Шаг 1. Создать сервер на Hetzner

1. Зарегистрируйся на [console.hetzner.cloud](https://console.hetzner.cloud/)
   (нужна карта — есть Израильская, подходит).
2. Создай новый проект.
3. **Add Server**:
   - Location: любой (Falkenstein/Nuremberg, для Telegram-бота задержка не критична).
   - Image: **Ubuntu 24.04**.
   - Type: **CX22** (2 vCPU, 4 ГБ RAM, 40 ГБ NVMe, ≈€4.35/мес).
   - SSH key: добавь свой публичный ключ (в Termius: Keychain → New Key,
     затем скопируй публичную часть сюда). Без пароля, только по ключу.
4. После создания сервера скопируй его **IP-адрес** — понадобится дальше.

## Шаг 2. Бесплатный домен через DuckDNS

1. Зайди на [duckdns.org](https://www.duckdns.org/), войди через GitHub/Google.
2. В поле "domains" впиши желаемое имя, например `ivrit-trainer` → жми **add domain**.
   Получится `ivrit-trainer.duckdns.org`.
3. В поле IP впиши IP-адрес сервера из шага 1, нажми **update ip**.
4. Подожди пару минут и проверь: `nslookup ivrit-trainer.duckdns.org` должен
   вернуть тот же IP.

## Шаг 3. Подключиться и настроить сервер

В Termius (или любом SSH-клиенте) подключись к серверу: `ssh root@<IP-адрес>`.

```bash
git clone https://github.com/Usachev13/hebrew-quiz-bot.git /tmp/hqb
cd /tmp/hqb
chmod +x deploy/*.sh
./deploy/setup_server.sh https://github.com/Usachev13/hebrew-quiz-bot.git
```

Это поставит Python, Caddy, создаст пользователя `botuser`, склонирует
репозиторий в `/opt/hebrew-quiz-bot` и поставит зависимости.

## Шаг 4. Токен

```bash
sudo -u botuser nano /opt/hebrew-quiz-bot/.env
```

Впиши:
```
TELEGRAM_TOKEN=сюда-токен-от-BotFather
BOT_DOMAIN=ivrit-trainer.duckdns.org
```
Сохрани (Ctrl+O, Enter, Ctrl+X в nano).

> **Токен — это пароль от бота, и он один.** Кто его знает, тот и есть
> бот: может переписать имя, описание и аватар, читать всё, что люди
> пишут боту, и отвечать от его имени. Отдельного «пароля администратора»
> у Telegram нет.
>
> Поэтому настоящий токен не пишется НИГДЕ, кроме `.env` на сервере —
> ни в этот файл, ни в примеры, ни в сообщения. Однажды он сюда попал
> как «просто пример из жизни», уехал с коммитом на GitHub, и бота
> переименовали в рекламу чужого канала. Репозиторий публичный, а такие
> строки на GitHub ищут автоматически — сутки на это не нужны.
>
> Если токен всё же где-то мелькнул: @BotFather → `/mybots` → бот →
> API Token → **Revoke current token**. Старый умирает сразу, и это
> единственное, что действительно помогает. Чистить историю git
> бессмысленно, пока токен жив, и не нужно, когда он уже отозван.

## Шаг 5. Запустить сервис и HTTPS

```bash
cd /opt/hebrew-quiz-bot
./deploy/install_service.sh ivrit-trainer.duckdns.org
```

Caddy сам получит сертификат Let's Encrypt для домена — никаких
дополнительных действий с certbot не нужно.

Проверка:
```bash
systemctl status hebrew-quiz-bot
curl -I https://ivrit-trainer.duckdns.org/
```
Второе должно вернуть `HTTP/2 200`.

## Шаг 6. Подключить вебхук

```bash
cd /opt/hebrew-quiz-bot
sudo -u botuser venv/bin/python3 set_webhook.py
```
В ответе должно быть `"ok": true`.

## Шаг 7. Проверка

Напиши боту `/start` в Telegram — должно ответить меню.

---

## Дальнейшие обновления

После каждого `git push` из PyCharm — на сервере:
```bash
cd /opt/hebrew-quiz-bot && sudo ./deploy/update.sh
```

## Если что-то не работает

```bash
systemctl status hebrew-quiz-bot          # запущен ли сам бот
journalctl -u hebrew-quiz-bot -n 50       # логи бота (traceback, если падает)
systemctl status caddy                    # жив ли Caddy
journalctl -u caddy -n 50                 # логи Caddy (проблемы с сертификатом и т.п.)
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"   # что видит Telegram
```
