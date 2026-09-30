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

import difflib
import html
import json
import os
import re

import requests

import hebrew_rules
import nakdan
from matching import _normalize

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
GOOGLE_KEY = os.environ.get("GOOGLE_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("DIALOG_MODEL_ANTHROPIC", "claude-haiku-4-5-20251001")
# Умолчание — gpt-4o, а не дешёвая mini. Не из осторожности: mini
# проверена на живом разговоре и иврита не знает. Она выдавала
# несуществующие слова («מָה תּוֹעֲדוֹת שֶׁלְּךָ?»), писала «אֲנִי גָּרָה
# בַּמַּשָּׁט» — «я живу в плавании» — и теряла перевод в четырёх репликах
# из пяти. Наши проверки такое не ловят: огласовки-то верные, их ставит
# Nakdan, а слова под ними выдуманы. Это ловит только человек.
OPENAI_MODEL = os.environ.get("DIALOG_MODEL_OPENAI", "gpt-4o")
# Протокол OpenAI стал общим языком: по нему говорят Groq, OpenRouter,
# Mistral, Together и локальная Ollama. Поэтому «openai» здесь — это не
# компания, а формат запроса, и сменой одного адреса мы получаем доступ
# ко всем ним, включая бесплатные. Отдельного кода они не требуют.
OPENAI_BASE = os.environ.get("OPENAI_BASE_URL",
                             "https://api.openai.com/v1").rstrip("/")
GOOGLE_MODEL = os.environ.get("DIALOG_MODEL_GOOGLE", "gemini-2.5-flash")
# Версия API. У разных ключей доступны разные: на одном работает
# v1beta, на другом только v1, и отличают они себя одинаковым 404.
GOOGLE_VERSIONS = ("v1beta", "v1")

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

SYSTEM = """Ты — {self_ru}, {self_who} разговаривает с новым
репатриантом, изучающим иврит. Твоя задача — РАЗГОВАРИВАТЬ, а не
преподавать. Говори о себе в {self_gender_ru} роде.

Правила речи, обязательные:
- Отвечай на современном разговорном иврите, каким говорят на улице, а
  не на книжном.
- Одна-две коротких фразы. Никогда не больше двух.
- Только простые слова уровня алеф: быт, знакомство, покупки, транспорт,
  врач, работа. Если без сложного слова не обойтись — объясни его тут же
  простыми словами.
- Огласовки (никуд) ставить не нужно: их расставит программа. Пиши
  обычным письмом, как пишут израильтяне.
- Задавай встречный вопрос почти в каждой реплике — иначе разговор
  оборвётся на второй фразе.
- Никогда не пиши транскрипцию русскими или латинскими буквами: её
  сделает программа.

Собеседник: {gender_ru}. Обращайся к нему в соответствующем роде.

Если человек написал на иврите с ошибкой, верни в поле fixed ЕГО ЖЕ
фразу целиком, исправленную. Не свою фразу, не совет, не пояснение —
ровно то, что он сказал, но правильно, слово в слово. Меняй только то,
что действительно неверно: лишние правки программа покажет человеку как
его ошибки. Если ошибок нет — оставь fixed пустым.

Пример: человек сказал «אני הולך לבית», правильно «אני הולך הביתה» ->
fixed = "אני הולך הביתה".

Если человек написал по-русски, ответь на иврите просто и коротко, а в
поле hint по-русски подскажи, как это же сказать на иврите.

Пример правильного ответа целиком:
{{"he": "שלום! מה שלומך היום?", "ru": "Привет! Как дела сегодня?",
  "fixed": "", "hint": ""}}

Поля he и ru заполнены ВСЕГДА, в каждом ответе без исключений. Ответ на
иврите без перевода бесполезен: человек его не прочтёт. Пустыми могут
быть только fixed и hint.

Отвечай ТОЛЬКО JSON, без пояснений вокруг:
{{"he": "ответ на иврите, обычным письмом — обязательно",
  "ru": "перевод этого же ответа на русский — обязательно",
  "fixed": "исправленная фраза человека или пустая строка",
  "hint": "подсказка по-русски или пустая строка"}}"""

SYSTEM_EN = SYSTEM.replace("на русский", "into English").replace(
    "по-русски", "in English")

GENDER_RU = {"m": "мужчина", "f": "женщина"}
SELF_RU = {"m": ("доброжелательный израильтянин", "который", "мужском"),
           "f": ("доброжелательная израильтянка", "которая", "женском")}


def _system(gender, lang, companion="f"):
    """Подсказка собеседнику.

    gender    — пол ученика: к нему обращаются в этом роде.
    companion — пол самого собеседника: в этом роде он говорит о себе.

    Две разные вещи, и в иврите слышны обе. Пока пол собеседника не
    задавался, он говорил о себе как придётся, а звучал всегда женским
    голосом — и «אֲנִי גָּר» женским голосом это готовая ошибка в ухо.
    """
    base = SYSTEM_EN if lang == "en" else SYSTEM
    who, rel, self_gender = SELF_RU.get(companion, SELF_RU["f"])
    return base.format(gender_ru=GENDER_RU.get(gender, "мужчина"),
                       self_ru=who, self_who=rel, self_gender_ru=self_gender)


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


# Схема ответа. Просьбы в подсказке «заполняй перевод всегда» модель
# выполняла через раз: gpt-4o-mini теряла перевод в четырёх репликах из
# пяти, gpt-4o — в одной. Схема со строгим режимом переносит требование
# из уговоров в протокол: служба не вернёт ответ без обязательных полей.
RESPONSE_SCHEMA = {
    "name": "reply",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["he", "ru", "fixed", "hint"],
        "properties": {
            "he": {"type": "string"},
            "ru": {"type": "string"},
            "fixed": {"type": "string"},
            "hint": {"type": "string"},
        },
    },
}


def _ask_openai(system, turns, schema=True):
    payload = {"model": OPENAI_MODEL, "max_tokens": 400,
               "messages": [{"role": "system", "content": system}] + turns}
    # Строгая схема есть не у всех, кто говорит на протоколе OpenAI:
    # Groq и OpenRouter принимают её не для каждой модели. Там, где
    # схему отвергли, просим ответ без неё — разбор у нас всё равно
    # терпимый.
    if schema:
        payload["response_format"] = {"type": "json_schema",
                                      "json_schema": RESPONSE_SCHEMA}
    r = requests.post(
        f"{OPENAI_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_KEY}",
                 "content-type": "application/json"},
        json=payload,
        timeout=TIMEOUT,
    )
    if schema and r.status_code == 400:
        return _ask_openai(system, turns, schema=False)
    r.raise_for_status()
    body = r.json()
    text = body["choices"][0]["message"]["content"]
    usage = body.get("usage") or {}
    return text, (usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))


def google_models():
    """Какие модели доступны этому ключу.

    Имена моделей у Google меняются, и «gemini-2.5-flash» на одном ключе
    работает, а на другом отвечает 404 без объяснений. Спрашивать имя у
    самой службы надёжнее, чем помнить его.
    """
    if not GOOGLE_KEY:
        return []
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                     headers={"x-goog-api-key": GOOGLE_KEY}, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for m in r.json().get("models", []):
        if "generateContent" in (m.get("supportedGenerationMethods") or []):
            out.append(m.get("name", "").replace("models/", ""))
    return out


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
    payload = {"system_instruction": {"parts": [{"text": system}]},
               "contents": contents,
               "generationConfig": {"maxOutputTokens": 400,
                                    "responseMimeType": "application/json"}}

    # 404 у Google значит не только «нет такой модели», но и «эта модель
    # недоступна в этой версии API». Первый заход подставлял сюда свою
    # догадку про имя — и получилось нелепо: бот сообщал, что модели нет,
    # а следом перечислял её же первой в списке доступных. Своими словами
    # чужую ошибку не пересказываем: показываем, что ответила служба, и
    # пробуем вторую версию API.
    def _why(resp):
        """Сообщение службы, а не сырой JSON.

        Первый заход резал r.text по трёхстам знакам — а Google
        печатает JSON с отступами, и на сам текст ошибки места уже не
        оставалось: человек видел «This model models/gemini» и всё.
        """
        try:
            return (resp.json().get("error") or {}).get("message") or resp.text
        except ValueError:
            return resp.text

    tried = []
    for version in GOOGLE_VERSIONS:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/{version}/models/"
            f"{GOOGLE_MODEL}:generateContent",
            headers={"x-goog-api-key": GOOGLE_KEY,
                     "content-type": "application/json"},
            json=payload, timeout=TIMEOUT,
        )
        if r.status_code != 404:
            break
        tried.append(f"{version} — {_why(r)}")
    else:
        try:
            names = ", ".join(google_models()[:10]) or "ни одной"
        except Exception:                                    # noqa: BLE001
            names = "не удалось спросить"
        raise RuntimeError(
            f"Google отвечает 404 на «{GOOGLE_MODEL}». Его словами:\n  "
            + "\n  ".join(tried)
            + f"\nДоступны этому ключу: {names}.")

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


def _key(word):
    """Слово в виде, пригодном для сравнения: без огласовок и знаков.

    Тот же нормализатор, что у проверки набранных ответов, — иначе
    «сравнение» здесь и «сравнение» там разойдутся.
    """
    return _normalize(word).strip(".,!?:;\u2026\u00ab\u00bb\"'()")


def mark_fix(said, fixed):
    """Фраза человека, записанная правильно, с отмеченными правками.

    Показываем ИСПРАВЛЕННУЮ фразу целиком, а не исходную: человек пишет
    без огласовок, и его собственная строка ему же нечитаема. Отмечено в
    ней только то, что действительно изменилось: лишнее зачёркнуто,
    нужное выделено.

    Сравниваем по согласным. Первый заход сравнивал как есть — и
    зачёркивал всю фразу целиком: у человека огласовок нет, у
    исправленной версии они есть, то есть отличается КАЖДОЕ слово.
    Выглядело так, будто он не сказал ни одного верного слова.

    Разметку считаем сами, а не просим у модели: попроси мы её
    расставить теги — она разметила бы то, что хотела бы исправить, а не
    то, что отличается от сказанного, и человек увидел бы «ошибки»,
    которых не делал.

    Сравниваем словами, а не буквами: правка в иврите почти всегда целое
    слово — предлог, форма, артикль, — а побуквенный разбор рассыпает
    слово на неузнаваемые куски.
    """
    a = (said or "").split()
    b = (fixed or "").split()
    if not a or not b:
        return ""
    ka, kb = [_key(w) for w in a], [_key(w) for w in b]
    if ka == kb:
        # Отличаются только огласовки — исправлять нечего. Это не правка,
        # а запись того же самого, и показывать её как ошибку нельзя.
        return ""
    out = []
    sm = difflib.SequenceMatcher(a=ka, b=kb, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out += [html.escape(w) for w in b[j1:j2]]
        else:
            if i1 != i2:
                out.append("<s>" + html.escape(" ".join(a[i1:i2])) + "</s>")
            if j1 != j2:
                out.append("<b>" + html.escape(" ".join(b[j1:j2])) + "</b>")
    return " ".join(out)


def strip_marks(text):
    return "".join(c for c in (text or "") if not (0x0591 <= ord(c) <= 0x05C7))


def _translate(he, lang="ru"):
    """Перевод одной реплики — когда модель забыла его в основном ответе."""
    target = "английский" if lang == "en" else "русский"
    system = (f"Переведи фразу с иврита на {target}. Ответь только "
              f"переводом, одной строкой, без кавычек и пояснений.")
    turns = [{"role": "user", "content": he}]
    try:
        ask = {"anthropic": _ask_anthropic, "google": _ask_google}.get(
            provider(), lambda s, t: _ask_openai(s, t, schema=False))
        text, usage = ask(system, turns)
    except Exception as e:                                   # noqa: BLE001
        print(f"[dialog] перевод не удался: {e}")
        _translate.last_usage = (0, 0)
        return ""
    _translate.last_usage = usage
    text = (text or "").strip().strip('"«»')
    # Схема здесь не нужна, но модель иногда всё равно отвечает JSON'ом.
    if text.startswith("{"):
        text = _parse(text).get("ru") or ""
    # Перевод с ивритскими буквами — не перевод. Первый заход брал поле
    # «he», если «ru» было пустым, и ученик получал в строке перевода тот
    # же иврит, что и выше. Лучше честное «перевода нет».
    if any("\u05d0" <= c <= "\u05ea" for c in text):
        return ""
    return _clean(text)


def reply(history, said, gender="m", lang="ru", companion="f"):
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

    system = _system(gender, lang, companion)
    ask = {"anthropic": _ask_anthropic, "openai": _ask_openai,
           "google": _ask_google}[provider()]
    raw, usage = ask(system, turns)
    data = _parse(raw)

    he = _clean(data.get("he"))
    fixed = _clean(data.get("fixed"))

    # Огласовки ставит Nakdan, а не модель. Просить их у модели оказалось
    # ненадёжно: на прямое указание с примером она всё равно отвечала
    # «שלום, אני בסדר», и наша транскрипция выдавала «шлвм, нй всдр».
    # Nakdan — огласовщик Бар-Иланского университета, он разбирает
    # контекст и потому различает то, что по буквам неразличимо.
    # Но своим выверенным формам мы верим больше: на пробе Nakdan из
    # тридцати фраз ошибся в семи, и всё это слова, которые у нас есть
    # («касса» он прочитал как «кофе», «два» — как «годы», а половину
    # инфинитивов увёл не в тот биньян). Поэтому vocalize_trusted:
    # Nakdan заполняет только то, чего у нас нет.
    # Недоступен — остаёмся с тем, что дала модель: разговор из-за
    # огласовок прерываться не должен.
    he = nakdan.vocalize_trusted(he) or he
    fixed = nakdan.vocalize_trusted(fixed) or fixed
    # Собственная проверка: огласовки модели никто не выверял, и если они
    # нарушают формальные правила — значит, порождено что-то странное.
    # Тогда снимаем огласовки: слово без них хотя бы читается взрослым
    # по контексту, а неверная огласовка учит неверному чтению.
    he, ok = hebrew_rules.sanitize(he)
    fixed, ok_fixed = hebrew_rules.sanitize(fixed)
    ru = _clean(data.get("ru"))
    if he and not ru:
        # Схема гарантирует, что поле ЕСТЬ, но не что оно не пустое:
        # строгий режим не умеет «строка не короче одного знака». Поэтому
        # страховка на нашей стороне — отдельный короткий запрос на один
        # перевод. Он стоит долю цента и случается редко, а ученик без
        # перевода не может прочесть ответ вовсе.
        ru = _translate(strip_marks(he), lang)
        extra = getattr(_translate, "last_usage", (0, 0))
        usage = (usage[0] + extra[0], usage[1] + extra[1])
    return {
        "he": he,
        "ru": ru,
        "no_ru": bool(he and not ru),
        "fixed": fixed,
        # Разметка правки: сравниваем сказанное с исправленным.
        "marked": mark_fix(said, fixed),
        "hint": _clean(data.get("hint")),
        "ok": ok and ok_fixed,
        "usage": usage,
        "raw": raw,
    }
