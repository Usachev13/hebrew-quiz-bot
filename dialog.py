# -*- coding: utf-8 -*-
"""
Свободный разговор на иврите.

Зачем отдельно от всего остального
----------------------------------
Всё, что есть в тренажёре, — это узнавание: увидел, вспомнил, выбрал.
Даже «сказать вслух» — повторение заданной фразы. Человек, прошедший
весь курс, умеет отвечать на вопросы приложения, но не умеет говорить:
разговор требует придумать своё предложение здесь и сейчас, и такой
задачи мы не ставили ни разу.

Здесь она ставится. Собеседник отвечает на то, что человек сказал, а не
сверяет с эталоном.

Чем это отличается от остального кода
-------------------------------------
ВСЁ остальное в проекте — выверенные данные: слова из словаря, формы
прогнаны через словарь форм, фразы ждут носителя. Здесь иврит порождает
модель, и НИКТО ЕГО НЕ ПРОВЕРЯЛ. Это сознательный размен: без него
разговора не будет вовсе, потому что заранее написать все ответы на всё,
что скажет человек, нельзя.

Отсюда три ограничения, которые здесь встроены:

1. Модель просят говорить просто и коротко — уровень алеф, две фразы
   максимум. Чем проще фраза, тем меньше в ней места для ошибки.
2. Ответ прогоняется через те же формальные правила, что и наш банк
   (`hebrew_rules`). Не прошёл — огласовки снимаем и транскрипцию не
   показываем: лучше без подсказки, чем с неверной.
3. Всё сказанное моделью пишется в журнал. Носитель сможет прочитать
   и сказать, годится ли это вообще.

Провайдер
---------
Ключ берётся из .env: ANTHROPIC_API_KEY или OPENAI_API_KEY, какой есть.
Своего мнения модуль не имеет — он умеет оба и выбирает по наличию
ключа. Нет ключа — разговор просто не предлагается, как и озвучка без
ключа Azure.
"""

import json
import os
import re

import requests

import hebrew_rules

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("DIALOG_MODEL_ANTHROPIC", "claude-haiku-4-5-20251001")
OPENAI_MODEL = os.environ.get("DIALOG_MODEL_OPENAI", "gpt-4o-mini")

# Сколько ходов разговора помним. Больше — дороже каждое сообщение:
# история уходит в модель целиком при каждом запросе.
HISTORY_TURNS = 8

# Ответ длиннее этого обрезаем: модель иногда забывает про «коротко», а
# начинающий в простыне текста тонет.
MAX_REPLY_CHARS = 300

TIMEOUT = 25


class NoKey(RuntimeError):
    """Ключа модели нет — разговор нельзя предлагать."""


def available():
    return bool(ANTHROPIC_KEY or OPENAI_KEY)


def provider():
    return "anthropic" if ANTHROPIC_KEY else ("openai" if OPENAI_KEY else "")


# --------------------------------------------------------------- подсказка

SYSTEM = """Ты — доброжелательный израильтянин, который разговаривает с
новым репатриантом, изучающим иврит. Твоя задача — РАЗГОВАРИВАТЬ, а не
преподавать.

Правила речи, обязательные:
- Отвечай на современном разговорном иврите, каким говорят на улице, а
  не на книжном.
- Одна-две коротких фразы. Никогда не больше двух.
- Только простые слова уровня алеф: быт, знакомство, покупки, транспорт,
  врач, работа. Если без сложного слова не обойтись — объясни его тут же
  простыми словами.
- Ставь огласовки (никуд) во всех ивритских словах: человек ещё не
  читает без них.
- Задавай встречный вопрос почти в каждой реплике — иначе разговор
  оборвётся на второй фразе.
- Никогда не пиши транскрипцию русскими или латинскими буквами: её
  сделает программа.

Собеседник: {gender_ru}. Обращайся к нему в соответствующем роде.

Если человек написал на иврите с ошибкой, которая мешает понять или
режет слух, — мягко дай правильный вариант в поле correction. Если
ошибок нет или они мелкие, оставь correction пустым. Не поправляй
дважды одно и то же.

Если человек написал по-русски, ответь на иврите просто и коротко, а в
поле hint по-русски подскажи, как это же сказать на иврите.

Отвечай ТОЛЬКО JSON, без пояснений вокруг:
{{"he": "ответ на иврите с огласовками",
  "ru": "перевод ответа на русский",
  "correction": "как надо было сказать, с огласовками, или пустая строка",
  "hint": "подсказка по-русски или пустая строка"}}"""

SYSTEM_EN = SYSTEM.replace("на русский", "into English").replace(
    "по-русски", "in English")

GENDER_RU = {"m": "мужчина", "f": "женщина"}


def _system(gender, lang):
    base = SYSTEM_EN if lang == "en" else SYSTEM
    return base.format(gender_ru=GENDER_RU.get(gender, "мужчина"))


# ----------------------------------------------------------------- запрос

def _ask_anthropic(system, turns):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": ANTHROPIC_MODEL, "max_tokens": 400,
              "system": system, "messages": turns},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    body = r.json()
    text = "".join(part.get("text", "") for part in body.get("content", []))
    usage = body.get("usage") or {}
    return text, (usage.get("input_tokens", 0), usage.get("output_tokens", 0))


def _ask_openai(system, turns):
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}",
                 "content-type": "application/json"},
        json={"model": OPENAI_MODEL, "max_tokens": 400,
              "messages": [{"role": "system", "content": system}] + turns},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    body = r.json()
    text = body["choices"][0]["message"]["content"]
    usage = body.get("usage") or {}
    return text, (usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


def _parse(text):
    """Достаём JSON из ответа.

    Модель иногда оборачивает его в ```json```, иногда добавляет фразу
    перед. Падать из-за этого нельзя: у человека посреди разговора
    пропадёт собеседник.
    """
    text = (text or "").strip()
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
    # Не JSON — считаем, что это и есть реплика на иврите.
    return {"he": text, "ru": "", "correction": "", "hint": ""}


def _clean(value):
    value = (value or "").strip()
    return value[:MAX_REPLY_CHARS]


def reply(history, said, gender="m", lang="ru"):
    """Ответ собеседника.

    history — [(роль, текст), …] прошлых ходов, роль «user» или «bot».
    said    — что человек сказал сейчас (иврит или русский).

    Возвращает словарь: he, ru, correction, hint, ok (прошёл ли ответ
    формальные правила), usage (токены на вход и выход).
    """
    if not available():
        raise NoKey("нет ключа языковой модели")

    turns = []
    for role, text in history[-HISTORY_TURNS * 2:]:
        turns.append({"role": "assistant" if role == "bot" else "user",
                      "content": text})
    turns.append({"role": "user", "content": said})

    system = _system(gender, lang)
    raw, usage = (_ask_anthropic(system, turns) if ANTHROPIC_KEY
                  else _ask_openai(system, turns))
    data = _parse(raw)

    he = _clean(data.get("he"))
    correction = _clean(data.get("correction"))
    # Собственная проверка: огласовки модели никто не выверял, и если они
    # нарушают формальные правила — значит, порождено что-то странное.
    # Тогда снимаем огласовки: слово без них хотя бы читается взрослым
    # по контексту, а неверная огласовка учит неверному чтению.
    he, ok = hebrew_rules.sanitize(he)
    correction, ok_corr = hebrew_rules.sanitize(correction)
    return {
        "he": he,
        "ru": _clean(data.get("ru")),
        "correction": correction,
        "hint": _clean(data.get("hint")),
        "ok": ok and ok_corr,
        "usage": usage,
        "raw": raw,
    }
