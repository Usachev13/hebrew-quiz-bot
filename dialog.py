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
Модуль умеет три и выбирает по наличию ключа в .env. Своего мнения он не
имеет: собеседнику нужны две короткие фразы бытового иврита, и с этим
справляется любая недорогая модель. Нет ключа — разговор просто не
предлагается, как и озвучка без ключа Azure.

Порядок выбора, если ключей несколько: Anthropic, OpenAI, Google. Он
произволен и значит лишь «какой-то один»; чтобы взять именно нужный,
уберите лишние ключи.

«OpenAI» здесь означает не компанию, а формат запроса: по нему говорят
и Groq, и OpenRouter, и Mistral, и локальная Ollama. Достаточно задать
OPENAI_BASE_URL — и любой из них становится доступен без единой строки
нового кода. Там же лежат бесплатные ключи, которые выдают без карты.

Про бесплатный Google отдельно. У него щедрый бесплатный предел (тысячи
запросов в день против наших сорока), и это правильный выбор, пока
тренажёром пользуется один человек. Но у бесплатного уровня есть цена,
которую платят не деньгами: разговоры уходят на улучшение чужих
продуктов. Для себя это неважно, для платного продукта с чужими
учениками — важно, и решать это надо до первого платящего, а не после.
"""

import json
import os
import re

import requests

import hebrew_rules

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("DIALOG_MODEL_ANTHROPIC", "claude-haiku-4-5-20251001")
OPENAI_MODEL = os.environ.get("DIALOG_MODEL_OPENAI", "gpt-4o-mini")
# Протокол OpenAI стал общим языком: по нему говорят Groq, OpenRouter,
# Mistral, Together и локальная Ollama. Поэтому «openai» здесь — это не
# компания, а формат запроса, и сменой одного адреса мы получаем доступ
# ко всем ним, включая бесплатные. Отдельного кода они не требуют.
OPENAI_BASE = os.environ.get("OPENAI_BASE_URL",
                             "https://api.openai.com/v1").rstrip("/")
GOOGLE_MODEL = os.environ.get("DIALOG_MODEL_GOOGLE", "gemini-2.5-flash")

# Сколько ходов разговора помним. Больше — дороже каждое сообщение:
# история уходит в модель целиком при каждом запросе.
HISTORY_TURNS = 8

# Ответ длиннее этого обрезаем: модель иногда забывает про «коротко», а
# начинающий в простыне текста тонет.
MAX_REPLY_CHARS = 300

TIMEOUT = 25


class NoKey(RuntimeError):
    """Ключа модели нет — разговор нельзя предлагать."""


KEYS = {"anthropic": lambda: ANTHROPIC_KEY,
        "openai": lambda: OPENAI_KEY,
        "google": lambda: GOOGLE_KEY}

# Порядок по умолчанию, когда ключей несколько и выбор не назван.
ORDER = ("anthropic", "openai", "google")


def available():
    return bool(provider())


def provider():
    """Кто ведёт разговор.

    Явный выбор (DIALOG_PROVIDER) сильнее наличия ключей — и это не
    украшение. В .env этого проекта уже лежал OPENAI_API_KEY, оставшийся
    от старых опытов с озвучкой. Молчаливый выбор «первый, у кого есть
    ключ» означал бы, что человек вписывает бесплатный ключ Google,
    перезапускает бота и получает отказ авторизации от OpenAI — при
    полностью верных настройках. Причину такого поведения ищут часами.
    """
    named = os.environ.get("DIALOG_PROVIDER", "").strip().lower()
    if named:
        # Назвали провайдера, а ключа к нему нет — это ошибка настройки,
        # и молча брать другого нельзя: человек получит не то, что
        # просил, и не узнает об этом.
        return named if KEYS.get(named, lambda: "")() else ""
    for name in ORDER:
        if KEYS[name]():
            return name
    return ""


def why_unavailable():
    """Почему разговора нет — словами, без ключей на экране."""
    named = os.environ.get("DIALOG_PROVIDER", "").strip().lower()
    if named and named not in KEYS:
        return (f"DIALOG_PROVIDER={named} — такого не знаю. "
                f"Возможные: {', '.join(KEYS)}")
    if named and not KEYS[named]():
        return f"Выбран {named}, но ключа к нему в .env нет."
    if not any(fn() for fn in KEYS.values()):
        return "Ни одного ключа модели в .env нет."
    return ""


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
        f"{OPENAI_BASE}/chat/completions",
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


def _ask_google(system, turns):
    """Gemini. Устроен иначе остальных двух, и в трёх местах.

    Роль собеседника называется «model», а не «assistant». Системная
    подсказка идёт отдельным полем, а не сообщением. И есть то, чего у
    других нет: можно потребовать ответ строго в JSON — тогда модель не
    обернёт его в ```json``` и не припишет фразу сверху. Разбор всё
    равно остаётся терпимым (_parse), потому что полагаться на чужое
    обещание формата — это и есть способ однажды остаться без
    собеседника посреди разговора.
    """
    contents = [{"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]} for m in turns]
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GOOGLE_MODEL}:generateContent",
        headers={"x-goog-api-key": GOOGLE_KEY, "content-type": "application/json"},
        json={"system_instruction": {"parts": [{"text": system}]},
              "contents": contents,
              "generationConfig": {"maxOutputTokens": 400,
                                   "responseMimeType": "application/json"}},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    body = r.json()
    try:
        parts = body["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError):
        # Ответа нет — чаще всего сработал фильтр безопасности. Пустая
        # строка уйдёт в _parse и превратится в пустую реплику, а бот
        # скажет «скажите ещё раз». Это лучше, чем исключение.
        text = ""
    usage = body.get("usageMetadata") or {}
    return text, (usage.get("promptTokenCount", 0),
                  usage.get("candidatesTokenCount", 0))


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
    ask = {"anthropic": _ask_anthropic, "openai": _ask_openai,
           "google": _ask_google}[provider()]
    raw, usage = ask(system, turns)
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
