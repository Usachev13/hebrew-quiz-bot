# -*- coding: utf-8 -*-
"""
Рассылка «слова дня». Запускается по расписанию systemd-таймером
(см. deploy/install_service.sh), а не изнутри веб-приложения.

Почему отдельным процессом: в боте нет своего планировщика, а держать
фоновый поток в gunicorn — лишний источник проблем при перезапусках.
Таймер просто дёргает этот скрипт раз в сутки.

Отправляем только тем, кто подписан и кому сегодня ещё не отправляли —
последнее защищает от дублей, если таймер сработает дважды.
"""

import sys

import bot
import db


def main():
    db.init_db()
    recipients = db.daily_word_recipients()
    if not recipients:
        print("Слово дня: получателей нет.")
        return 0

    sent = failed = 0
    for chat_id in recipients:
        try:
            bot.send_word_of_day(chat_id, lang=db.resolve_lang(chat_id))
            db.mark_daily_word_sent(chat_id)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"Слово дня: не удалось отправить {chat_id}: {e}")

    print(f"Слово дня: отправлено {sent}, ошибок {failed}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
