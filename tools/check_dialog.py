# -*- coding: utf-8 -*-
"""
Проверка разговора.

Что здесь проверяется
---------------------
Разговор — единственное место в проекте, где иврит порождает машина, а
не берётся из выверенных данных. Проверить ПРАВИЛЬНОСТЬ того, что она
скажет, нельзя ни здесь, ни вообще: это работа носителя, и реплики для
этого пишутся в базу.

Но можно проверить всё остальное, и это не мелочь:

1. Разбор ответа. Модель отвечает JSON'ом, и делает это не всегда
   аккуратно: оборачивает в ```json```, добавляет фразу перед. Упасть
   на этом нельзя — у человека посреди беседы пропадёт собеседник.
2. Отношение к сомнительным огласовкам. Если модель прислала запись,
   нарушающую формальные правила, огласовки снимаются, а транскрипция
   не показывается. Это главное обещание модуля: лучше без подсказки,
   чем с неверной.
3. Предел на сутки. Считать его надо ДО обращения к модели, иначе мы
   платим за сообщение, которое не покажем.

К модели эта проверка не ходит: ответы подменяются. Иначе она стоила бы
денег при каждом запуске и зависела бы от сети.
"""

import os
import sys
import tempfile

os.environ.setdefault("BOT_DB_PATH", tempfile.mktemp(suffix=".db"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import db  # noqa: E402
import dialog  # noqa: E402
import hebrew_rules  # noqa: E402

fails = []


def check(title, ok, detail=""):
    if ok:
        print(f"✓ {title}")
    else:
        fails.append(title)
        print(f"  СБОЙ {title}: {detail}")


# ------------------------------------------------------------- разбор
GOOD = '{"he": "שָׁלוֹם! מַה שְׁלוֹמְךָ?", "ru": "Привет! Как дела?", ' \
       '"correction": "", "hint": ""}'
SHAPES = {
    "чистый JSON": GOOD,
    "в блоке кода": "```json\n" + GOOD + "\n```",
    "с приговоркой": "Вот ответ:\n" + GOOD,
    "с переводом строки внутри": GOOD.replace(", ", ",\n  "),
}
for name, raw in SHAPES.items():
    data = dialog._parse(raw)
    check(f"разбирается: {name}",
          data.get("he", "").startswith("שָׁלוֹם"), repr(data)[:120])

# Совсем не JSON — считаем всё сказанное репликой, а не падаем.
data = dialog._parse("שָׁלוֹם")
check("не-JSON не роняет разговор", data.get("he") == "שָׁלוֹם", repr(data))
check("пустой ответ не роняет разговор",
      isinstance(dialog._parse(""), dict) and isinstance(dialog._parse(None), dict))


# ------------------------------------------------------- три провайдера
# Ответ у каждого устроен по-своему, и разбирается своим куском кода.
# Подменяем сам HTTP-вызов и проверяем, что из трёх разных форм ответа
# выходит одно и то же: текст реплики и счёт токенов. Ошибка тут
# означала бы, что разговор работает с одним провайдером и молча ломается
# при переезде на другой.
class FakeResponse:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


SHAPES_BY_PROVIDER = {
    "anthropic": (dialog._ask_anthropic, {
        "content": [{"type": "text", "text": GOOD}],
        "usage": {"input_tokens": 120, "output_tokens": 40}}),
    "openai": (dialog._ask_openai, {
        "choices": [{"message": {"content": GOOD}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 40}}),
    "google": (dialog._ask_google, {
        "candidates": [{"content": {"parts": [{"text": GOOD}]}}],
        "usageMetadata": {"promptTokenCount": 120, "candidatesTokenCount": 40}}),
}

real_post = dialog.requests.post
for name, (fn, body) in SHAPES_BY_PROVIDER.items():
    dialog.requests.post = lambda *a, **k: FakeResponse(body)
    try:
        text, usage = fn("подсказка", [{"role": "user", "content": "שלום"}])
    finally:
        dialog.requests.post = real_post
    check(f"ответ разобран: {name}",
          dialog._parse(text).get("he", "").startswith("שָׁלוֹם")
          and usage == (120, 40), f"{text[:60]!r} {usage}")

# Пустой ответ (сработал фильтр, оборвалась выдача) не должен ронять
# разговор ни у одного из трёх.
EMPTY = {"anthropic": {"content": []},
         "openai": {"choices": [{"message": {"content": ""}}]},
         "google": {"candidates": []}}
for name, body in EMPTY.items():
    fn = SHAPES_BY_PROVIDER[name][0]
    dialog.requests.post = lambda *a, **k: FakeResponse(body)
    try:
        if name == "openai":
            text, _ = fn("п", [{"role": "user", "content": "ש"}])
        else:
            text, _ = fn("п", [{"role": "user", "content": "ש"}])
        ok = isinstance(dialog._parse(text), dict)
    except Exception as e:                                  # noqa: BLE001
        ok = False
        text = f"исключение: {e}"
    finally:
        dialog.requests.post = real_post
    check(f"пустой ответ не роняет: {name}", ok, str(text)[:60])

# Выбор провайдера — по ключу, и порядок объявлен.
saved = (dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY)
for keys, expected in ((("a", "", ""), "anthropic"), (("", "o", ""), "openai"),
                       (("", "", "g"), "google"), (("a", "o", "g"), "anthropic"),
                       (("", "", ""), "")):
    dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY = keys
    check(f"выбор провайдера {keys} -> {expected or 'ничего'}",
          dialog.provider() == expected, dialog.provider())
check("без ключей разговор недоступен", not dialog.available())
dialog.ANTHROPIC_KEY, dialog.OPENAI_KEY, dialog.GOOGLE_KEY = saved


# ------------------------------------------- сомнительные огласовки
# Каф без шва — формальная ошибка, значит записи модели верить нельзя.
DIRTY = "הוֹלֵך לַבַּיִת"
clean_text, ok = hebrew_rules.sanitize(DIRTY)
check("сомнительная огласовка снимается", not ok and "ֵ" not in clean_text,
      f"{clean_text!r} ok={ok}")

GOOD_HE = "שָׁלוֹם, מַה שְׁלוֹמְךָ?"
kept, ok = hebrew_rules.sanitize(GOOD_HE)
check("хорошая огласовка сохраняется", ok and kept == GOOD_HE, f"{kept!r} ok={ok}")

# И главное: при сомнительной записи транскрипция не показывается.
import bot  # noqa: E402

check("при сомнительной записи транскрипции нет",
      bot._reading_if_clean(DIRTY, False, "ru") == "",
      bot._reading_if_clean(DIRTY, False, "ru"))
check("при хорошей записи транскрипция есть",
      bool(bot._reading_if_clean(GOOD_HE, True, "ru")))


# -------------------------------------------------------------- предел
db.init_db()
CHAT = 424242
check("лимит берётся из настроек", db.dialog_left(CHAT) == db.DIALOG_DAILY_LIMIT,
      db.dialog_left(CHAT))
for i in range(db.DIALOG_DAILY_LIMIT):
    db.dialog_add(CHAT, "user", f"реплика {i}")
check("предел исчерпывается", db.dialog_left(CHAT) == 0, db.dialog_left(CHAT))

# Реплики бота предел не тратят: считаем то, что сказал человек.
before = db.dialog_left(CHAT + 1)
db.dialog_add(CHAT + 1, "bot", "שָׁלוֹם")
check("ответы бота не тратят предел", db.dialog_left(CHAT + 1) == before)

# История возвращается в порядке разговора, иначе модель отвечает невпопад.
db.dialog_reset(CHAT)
for role, text in (("user", "раз"), ("bot", "два"), ("user", "три")):
    db.dialog_add(CHAT, role, text)
hist = db.dialog_history(CHAT)
check("история в порядке разговора",
      [x[1] for x in hist] == ["раз", "два", "три"], hist)

# Сброс не трогает чужие разговоры.
db.dialog_add(CHAT + 2, "user", "чужое")
db.dialog_reset(CHAT)
check("сброс не задевает соседей", len(db.dialog_history(CHAT + 2)) == 1)

# Расход считается по токенам, а не по числу сообщений.
db.dialog_reset(CHAT + 2)
db.dialog_add(CHAT, "bot", "שָׁלוֹם", (100, 20))
db.dialog_add(CHAT, "bot", "טוֹב", (50, 10), clean=False)
spend = db.dialog_spend()
check("расход считается", spend.get("tin") == 150 and spend.get("tout") == 30, spend)
check("нечистые ответы считаются отдельно", spend.get("dirty") == 1, spend)


# ------------------------------------------------- подсказка собеседнику
system = dialog._system("f", "ru")
check("род собеседника попадает в подсказку", "женщина" in system)
check("подсказка требует огласовок", "огласовк" in system.lower())
check("подсказка запрещает транскрипцию", "транскрипц" in system.lower())

print()
print(f"Без ключа модели разговор недоступен и не предлагается: "
      f"available={dialog.available()}")
print("Правильность ивритa собеседника машина не проверяет — реплики "
      "пишутся в базу, чтобы их прочитал носитель.")
if fails:
    print(f"\nСБОЕВ: {len(fails)}")
    sys.exit(1)
