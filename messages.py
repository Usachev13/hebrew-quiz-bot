# -*- coding: utf-8 -*-
"""
Тексты чат-бота на двух языках.

Что сюда попадает и что нет
---------------------------
Сюда — всё, что читает человек: кнопки, вопросы, приветствие, статистика.
Не сюда — сообщения в журнал (`print("[start_round] БД недоступна…")`).
Их читает тот, кто чинит сервер, и переводить их значило бы усложнить
себе же разбор аварии ради никого.

Живые реплики бота («✅ В точку», «🔥 Пять подряд») лежат отдельно, в
reactions.py: там пулы, из которых выбирается случайная, и структура
другая.

Подстановки
-----------
Через именованные поля: `t("round.start", lang, label=..., total=...)`.
Порядок слов в языках разный, и склеивать строку плюсами нельзя — в
английском «Round «food», 10 questions» и в русском «Раунд «еда», 10
вопросов» совпали случайно, а вот «10 of 26 mastered» и «10 из 26
закреплено» уже нет.

Множественное число
-------------------
Формы хранятся через «|»: в русском три, в английском две. Выбирает
plural() — правило принадлежит языку, а не месту вызова. До этого в
bot.py стояла функция plural(n, one, few, many) с тремя русскими
формами прямо в аргументах; для английского она бессмысленна.
"""

DEFAULT = "ru"


def plural(n, key, lang=DEFAULT):
    """Нужная форма слова при числе n. `key` — ключ с формами через «|»."""
    forms = text(key, lang).split("|")
    if lang != "ru":
        return forms[0] if abs(n) == 1 else forms[-1]
    a, b = abs(n) % 100, abs(n) % 10
    if 10 < a < 20:
        return forms[2]
    if b == 1:
        return forms[0]
    if 2 <= b <= 4:
        return forms[1]
    return forms[2]


def text(key, lang=DEFAULT):
    """Строка по ключу. Нет перевода — откатываемся на русский.

    Откат, а не пустота: увидеть русскую строку в английском боте
    неприятно, но пережить можно, а пустая кнопка не нажимается.
    Недостачу называет tools/check_i18n.py.
    """
    item = M.get(key)
    if item is None:
        return key
    return item.get(lang) or item[DEFAULT]


def t(key, lang=DEFAULT, **vars):
    """Строка с подстановками."""
    s = text(key, lang)
    return s.format(**vars) if vars else s


M = {
# ---------------------------------------------------------- слова с числом
"n.section": {"ru": "раздел|раздела|разделов", "en": "section|sections"},
"n.card": {"ru": "карточка|карточки|карточек", "en": "card|cards"},
"n.word": {"ru": "слово|слова|слов", "en": "word|words"},
"n.infinitive": {"ru": "инфинитив|инфинитива|инфинитивов",
                 "en": "infinitive|infinitives"},
"n.form": {"ru": "форма|формы|форм", "en": "form|forms"},
"n.verb": {"ru": "глагол|глагола|глаголов", "en": "verb|verbs"},
"n.day": {"ru": "день|дня|дней", "en": "day|days"},
"n.error": {"ru": "ошибка|ошибки|ошибок", "en": "mistake|mistakes"},
"n.question": {"ru": "вопрос|вопроса|вопросов", "en": "question|questions"},

# ------------------------------------------------------------- приветствие
"welcome": {
"ru": "Здесь две вещи, и они разные.\n\n"
      "<b>В этом чате с вами разговаривают на иврите.</b> Скажите "
      "<b>שלום</b> — голосом или текстом — и вам ответят. Дальше просто "
      "разговаривайте: собеседник отвечает на то, что вы сказали, "
      "поправляет фразу, если она построена не так, переводит каждую "
      "свою реплику и спрашивает в ответ. Не знаете, как сказать, — "
      "скажите по-русски, вам подскажут ивритом.\n\n"
      "<b>В приложении — всё остальное.</b> Алфавит с нуля, {words} {words_w} "
      "по темам, {verbs} {verbs_w} во всех временах, разговорные фразы для "
      "банка, врача и съёма квартиры. Каждое слово озвучено живым "
      "ивритским голосом и показано с ударением. Что даётся тяжело — "
      "возвращается чаще: через день, три, неделю, три недели.\n\n"
      "Начните с кнопки ниже. Если буквы ещё не читаются — там есть "
      "алфавит, а тест уровня подскажет, откуда начинать.\n\n"
      "Подробнее — /about",
"en": "There are two things here, and they are different.\n\n"
      "<b>In this chat people talk to you in Hebrew.</b> Say "
      "<b>שלום</b> — by voice or by text — and you'll get an answer. "
      "Then just talk: your companion replies to what you actually "
      "said, corrects the sentence if it came out wrong, translates "
      "every line and asks you something back. If you don't know how to "
      "say it, say it in English and you'll be told the Hebrew.\n\n"
      "<b>The app holds everything else.</b> The alphabet from scratch, "
      "{words} {words_w} by topic, {verbs} {verbs_w} in every tense, spoken phrases for "
      "the bank, the doctor and renting a flat. Every word is voiced by "
      "a real Hebrew voice and shown with its stress. Whatever is hard "
      "comes back more often: in a day, three days, a week, three "
      "weeks.\n\n"
      "Start with the button below. If the letters don't read yet, the "
      "alphabet is in there, and the placement test will tell you where "
      "to begin.\n\n"
      "More — /about",
},

# ----------------------------------------------------------- разговор
"menu.talk": {"ru": "💬 Поговорить на иврите", "en": "💬 Talk in Hebrew"},
"talk.intro": {
"ru": "Говорите. Голосом или текстом, на иврите или по-русски.\n\n"
      "Начните с <b>שלום</b> — вам ответят и спросят, как дела.\n\n"
      "Сейчас с вами говорит {who}. В иврите это слышно в самих словах, "
      "поэтому собеседника можно сменить кнопкой ниже.\n\n"
      "Сегодня осталось реплик: {left}.",
"en": "Go ahead. Voice or text, Hebrew or English.\n\n"
      "Start with <b>שלום</b> — you'll get an answer and a question "
      "back.\n\nYou're talking to {who}. In Hebrew this is audible in "
      "the words themselves, so you can switch with the button "
      "below.\n\nReplies left today: {left}.",
},
"talk.restart": {"ru": "Начать разговор заново", "en": "Start over"},
"talk.who.m": {"ru": "мужчина", "en": "a man"},
"talk.who.f": {"ru": "женщина", "en": "a woman"},
"talk.switch.m": {"ru": "👨 Пусть отвечает мужчина",
                  "en": "👨 Let a man answer"},
"talk.switch.f": {"ru": "👩 Пусть отвечает женщина",
                  "en": "👩 Let a woman answer"},
"talk.switched.m": {
"ru": "Теперь с вами говорит мужчина — и голосом, и формами слов. "
      "Разговор начат заново.",
"en": "You're talking to a man now — both the voice and the word forms. "
      "The conversation starts over.",
},
"talk.switched.f": {
"ru": "Теперь с вами говорит женщина — и голосом, и формами слов. "
      "Разговор начат заново.",
"en": "You're talking to a woman now — both the voice and the word "
      "forms. The conversation starts over.",
},
"talk.reset": {"ru": "Хорошо, забыли. О чём поговорим?",
               "en": "Fine, forgotten. What shall we talk about?"},
"talk.showText": {"ru": "📄 Текст", "en": "📄 Text"},
"talk.listen": {"ru": "🎧 Послушайте ответ",
                "en": "🎧 Listen to the answer"},
"talk.noText": {"ru": "Текста уже нет — скажите что-нибудь ещё.",
                "en": "That text is gone — say something else."},
"talk.better": {"ru": "💡 {text}", "en": "💡 {text}"},
"talk.hint": {"ru": "Подсказка: {text}", "en": "Hint: {text}"},
"talk.off": {
"ru": "Разговор пока не подключён — не хватает ключа модели. "
      "Упражнения работают в приложении.",
"en": "Conversation isn't connected yet — the model key is missing. "
      "The exercises work in the app.",
},
"talk.limit": {
"ru": "На сегодня разговор окончен — вернёмся завтра. "
      "А упражнения в приложении без ограничений.",
"en": "That's it for today's conversation — let's continue tomorrow. "
      "The exercises in the app have no limit.",
},
"talk.failed": {
"ru": "Собеседник не ответил. Скажите ещё раз.",
"en": "No answer came back. Say it again.",
},
"moved": {
"ru": "Упражнения переехали в приложение — кнопка ниже. "
      "В чате остался разговор: просто напишите или наговорите "
      "что-нибудь на иврите.",
"en": "The exercises have moved to the app — button below. "
      "The chat is for conversation now: just write or say something "
      "in Hebrew.",
},

# ---------------------------------------------------------------- /about
# Собирается из кусков, потому что числа считаются по фактическим пулам:
# словарь пополняется, и записанная руками цифра разойдётся с правдой.
"about.head": {"ru": "<b>Что здесь есть</b>", "en": "<b>What's here</b>"},
"about.talk": {
"ru": "💬 <b>Разговор</b> — здесь с вами говорят на иврите, и это "
      "единственное, что живёт в чате. Собеседник отвечает на "
      "сказанное, а не сверяет с заготовкой: поправляет фразу, если "
      "она построена не так, переводит каждую свою реплику и "
      "спрашивает в ответ. Говорить можно голосом или текстом, на "
      "иврите или на своём языке.\n"
      "Честно про устройство: иврит собеседника порождает языковая "
      "модель. Всё остальное в тренажёре выверено по словарям, а это — "
      "нет, поэтому реплики короткие и простые, а сомнительные "
      "огласовки снимаются вместе с транскрипцией.",
"en": "💬 <b>Conversation</b> — this is where people talk to you in "
      "Hebrew, and it is the only thing left in the chat. Your "
      "companion answers what you actually said instead of matching it "
      "against a script: it corrects the sentence if it came out wrong, "
      "translates every line and asks you something back. Speak by "
      "voice or by text, in Hebrew or in your own language.\n"
      "Plainly about how it works: the companion's Hebrew is produced "
      "by a language model. Everything else in the trainer is checked "
      "against dictionaries; this is not, so the lines are kept short "
      "and simple, and doubtful vowel marks are dropped along with the "
      "transcription.",
},
"about.say": {
"ru": "🗣 <b>Заговорить</b> — {say} готовых фраз в {situations} "
      "ситуациях: макколет и кафе, банк и купат холим, съём квартиры, "
      "знакомство. Сначала говорите вслух, потом смотрите ответ — "
      "молча упражнение не работает. Формы для мужчины и женщины "
      "разные, потому что в иврите глагол меняется по полу говорящего.",
"en": "🗣 <b>Start speaking</b> — {say} ready phrases across {situations} "
      "situations: the corner shop and the café, the bank and the health "
      "fund, renting a flat, meeting people. Say it out loud first, then "
      "look at the answer — silently the exercise does not work. The "
      "forms differ for men and women, because in Hebrew the verb "
      "changes with the speaker's gender.",
},
"about.alef": {
"ru": "🔤 <b>Алфавит</b> — {modes} {modes_w}, {cards} {cards_w}: "
      "названия и звуки букв, конечные формы, дагеш "
      "(почему בּ читается «б», а ב — «в»), огласовки, чтение слогов. "
      "Разделы идут по порядку: от узнавания к чтению.",
"en": "🔤 <b>Alphabet</b> — {modes} {modes_w}, {cards} {cards_w}: "
      "letter names and sounds, final forms, the dagesh "
      "(why בּ reads «b» and ב reads «v»), vowel signs, reading "
      "syllables. The sections run in order: from recognising to reading.",
},
"about.words": {
"ru": "📚 <b>Слова</b> — {topic_words} {words_w} в {topics} бытовых темах "
      "(еда, семья, дом, город, здоровье, покупки…) "
      "и ещё {gram_words} в {gram} грамматических группах: "
      "прилагательные, местоимения, числительные, предлоги места.",
"en": "📚 <b>Words</b> — {topic_words} {words_w} across {topics} everyday "
      "topics (food, family, home, city, health, shopping…) "
      "and another {gram_words} in {gram} grammar groups: adjectives, "
      "pronouns, numbers, prepositions of place.",
},
"about.verbs": {
"ru": "🔁 <b>Глаголы</b> — {verbs} {verbs_w} и {forms} {forms_w} "
      "прошедшего, настоящего и будущего времени. Формы не набраны "
      "вручную, а выведены по правилам биньянов — поэтому их столько.",
"en": "🔁 <b>Verbs</b> — {verbs} {verbs_w} and {forms} {forms_w} in the "
      "past, present and future. The forms were not typed by hand but "
      "derived from the binyan rules — which is why there are so many.",
},
"about.voice": {
"ru": "🎧 <b>Озвучка</b> — произношение голосом, можно помедленнее. "
      "Ударения размечены вручную, включая исключения вроде "
      "בַּיִת и לָמָּה.",
"en": "🎧 <b>Audio</b> — spoken pronunciation, slower if you like. "
      "Stress is marked by hand, including exceptions such as "
      "בַּיִת and לָמָּה.",
},
"about.leitner": {
"ru": "🧠 <b>Интервальные повторения</b> — пять коробок по Лейтнеру. "
      "«Выучено» ставится не за один верный ответ, а за три с растущими "
      "промежутками.",
"en": "🧠 <b>Spaced repetition</b> — five Leitner boxes. «Learned» is not "
      "given for one correct answer but for three, at growing intervals.",
},
"about.formats": {
"ru": "🎮 <b>Три формата</b> — выбрать из вариантов, написать самому, "
      "собрать слово из букв. Ответ засчитывается и без огласовок, и с "
      "опечаткой в одну букву.",
"en": "🎮 <b>Three formats</b> — pick from options, type it yourself, "
      "build the word from letters. An answer counts without vowel signs, "
      "and with a one-letter typo.",
},
"about.app": {
"ru": "📱 <b>Приложение</b> — прогресс по темам, слабые места, уровни и "
      "серия дней. Открывается кнопкой ниже.",
"en": "📱 <b>The app</b> — progress by topic, weak spots, levels and your "
      "daily streak. Open it with the button below.",
},
"about.daily": {
"ru": "🗓 <b>Слово дня</b> по утрам — /daily_on и /daily_off.",
"en": "🗓 <b>Word of the day</b> each morning — /daily_on and /daily_off.",
},
"about.missing": {
"ru": "<b>Чего пока нет:</b> проверки произношения на слух, разбора "
      "корня и модели (шореш и мишкаль), разговора с ИИ. Распознавание "
      "речи — следующий шаг: сейчас вы сами отмечаете, получилось "
      "сказать или нет.",
"en": "<b>What's missing so far:</b> checking your pronunciation by ear, "
      "breaking words into root and pattern (shoresh and mishkal), "
      "conversation with an AI. Speech recognition is the next step — "
      "for now you mark yourself whether you managed to say it.",
},
"about.commands": {
"ru": "Команды: /talk · /word · /stats · /voices · /speed · /lang",
"en": "Commands: /talk · /word · /stats · /voices · /speed · /lang",
},

# ---------------------------------------------------------------- меню
"menu.app": {"ru": "📱 Открыть приложение", "en": "📱 Open the app"},
"menu.words": {"ru": "📚 Слова и грамматика", "en": "📚 Words and grammar"},
"menu.alphabet": {"ru": "🔤 Алфавит (с нуля)", "en": "🔤 Alphabet (from scratch)"},
"menu.wordOfDay": {"ru": "🗓 Слово дня", "en": "🗓 Word of the day"},
"menu.stats": {"ru": "📊 Статистика", "en": "📊 Statistics"},
"menu.topics": {"ru": "🗂 По темам", "en": "🗂 By topic"},
"menu.grammar": {"ru": "✏️ Грамматика", "en": "✏️ Grammar"},
"menu.verbs": {"ru": "🔤 Глаголы", "en": "🔤 Verbs"},
"menu.weak": {"ru": "⚡ Мои слабые места", "en": "⚡ My weak spots"},
"menu.back": {"ru": "‹ Назад", "en": "‹ Back"},
"menu.toMenu": {"ru": "‹ Меню", "en": "‹ Menu"},
"menu.mix": {"ru": "🎲 Всё вперемешку", "en": "🎲 Everything mixed"},
"menu.infinitives": {"ru": "🔤 Инфинитивы", "en": "🔤 Infinitives"},
"menu.past": {"ru": "⏪ Прошедшее", "en": "⏪ Past"},
"menu.present": {"ru": "▶️ Настоящее", "en": "▶️ Present"},
"menu.future": {"ru": "⏩ Будущее", "en": "⏩ Future"},
"menu.gapVerb": {"ru": "📝 Дополни фразу: глагол",
                 "en": "📝 Fill the gap: verb"},
"menu.gapWho": {"ru": "📝 Дополни фразу: кто",
                "en": "📝 Fill the gap: who"},
"menu.choice": {"ru": "🔘 Выбрать из вариантов", "en": "🔘 Pick from options"},
"menu.type": {"ru": "⌨️ Написать самому", "en": "⌨️ Type it yourself"},
"menu.anagram": {"ru": "🔡 Собрать из букв", "en": "🔡 Build from letters"},
"menu.trainWeak": {"ru": "⚡ Потренировать эти", "en": "⚡ Practise these"},
"menu.trainWords": {"ru": "📖 Потренировать слова", "en": "📖 Practise words"},

"ask.today": {"ru": "Что тренируем сегодня?", "en": "What shall we practise today?"},
"ask.what": {"ru": "Что тренируем?", "en": "What shall we practise?"},
"ask.topic": {"ru": "Выбери тему:", "en": "Pick a topic:"},
"menu.speak": {"ru": "🎙 Сказать вслух", "en": "🎙 Say it aloud"},
"speak.task": {"ru": "Скажите вслух на иврите:\n<b>{ru}</b>",
               "en": "Say this in Hebrew:\n<b>{ru}</b>"},
"speak.hint": {"ru": "<i>Запишите голосовое — я расшифрую и сравню. "
                     "Проверяю, узнаётся ли фраза; ударение распознавание "
                     "не слышит.</i>",
               "en": "<i>Record a voice message — I will transcribe and "
                     "compare it. I check whether the phrase is "
                     "recognisable; recognition does not hear stress.</i>"},
"speak.show": {"ru": "Показать фразу", "en": "Show the phrase"},
"speak.retry": {"ru": "Сказать ещё раз", "en": "Say it again"},
"speak.next": {"ru": "Другая фраза", "en": "Another phrase"},
"speak.heard": {"ru": "Услышал: <b>{text}</b>", "en": "I heard: <b>{text}</b>"},
"speak.expected": {"ru": "Ожидал: {text}", "en": "Expected: {text}"},
"speak.missing": {"ru": "Не хватает: {words}", "en": "Missing: {words}"},
"speak.extra": {"ru": "Лишнее: {words}", "en": "Extra: {words}"},
"speak.unsure": {"ru": "<i>Запись неразборчивая — расшифровка могла "
                       "переврать. Попробуйте в тишине и ближе к микрофону.</i>",
                 "en": "<i>The recording is unclear, so the transcript may be "
                       "wrong. Try again somewhere quiet, closer to the mic.</i>"},
"speak.v.match": {"ru": "✅ Фраза узнаётся полностью.",
                  "en": "✅ The phrase is fully recognisable."},
"speak.v.close": {"ru": "🟡 Почти: одно слово разошлось.",
                  "en": "🟡 Almost: one word differs."},
"speak.v.different": {"ru": "❌ Услышал другое.",
                      "en": "❌ I heard something else."},
"speak.v.silence": {"ru": "🤫 Ничего не разобрал — тишина или слишком тихо.",
                    "en": "🤫 I could not make anything out — silence or too quiet."},
"speak.noTask": {"ru": "Сначала выберите «Сказать вслух» — я дам фразу.",
                 "en": "Pick “Say it aloud” first and I will give you a phrase."},
"speak.tooLong": {"ru": "Слишком длинная запись. Одна фраза — этого хватит.",
                  "en": "That recording is too long. One phrase is enough."},
"speak.failed": {"ru": "Не смог разобрать запись. Попробуйте ещё раз.",
                 "en": "I could not process the recording. Please try again."},
"speak.off": {"ru": "Разбор голоса сейчас недоступен.",
              "en": "Voice checking is unavailable right now."},
"q.itWas": {"ru": "Это было: {word}",
            "en": "It was: {word}"},
"q.askListen": {"ru": "Послушайте и выберите перевод:",
                "en": "Listen and pick the meaning:"},
"q.noVoice": {"ru": "Не смог отправить запись — попробуйте ещё раз.",
              "en": "Could not send the recording — please try again."},
"menu.listen": {"ru": "🎧 На слух",
                "en": "🎧 By ear"},
"menu.abbrev": {"ru": "🔤 Сокращения",
                "en": "🔤 Abbreviations"},
"menu.plural": {"ru": "🔢 Один и много",
                "en": "🔢 One and many"},
"menu.syntax": {"ru": "🧩 Собери фразу",
                "en": "🧩 Build the sentence"},
"menu.numerals": {"ru": "🔢 Сколько чего",
                  "en": "🔢 How many of what"},
"menu.prep": {"ru": "🔗 Предлоги с местоимениями",
              "en": "🔗 Prepositions with pronouns"},
"menu.smichut": {"ru": "🏠 Смихут", "en": "🏠 Construct state"},
"menu.kol": {"ru": "♾ Каждый, весь, все", "en": "♾ Every, whole, all"},
"menu.she": {"ru": "🪢 Который и что", "en": "🪢 Which and that"},
"ask.grammar": {"ru": "Что из грамматики?", "en": "Which part of grammar?"},
"ask.verbs": {"ru": "Глаголы — что тренируем?", "en": "Verbs — what shall we practise?"},
"ask.format": {"ru": "Как отвечаем?", "en": "How do we answer?"},

# ------------------------------------------------------------- алфавит
"alef.table": {"ru": "📜 Показать весь алфавит", "en": "📜 Show the whole alphabet"},
"alef.names": {"ru": "Названия букв", "en": "Letter names"},
"alef.sounds": {"ru": "Звуки букв", "en": "Letter sounds"},
"alef.byName": {"ru": "Узнать по названию", "en": "Find it by name"},
"alef.finals": {"ru": "Конечные формы", "en": "Final forms"},
"alef.niqqud": {"ru": "Огласовки", "en": "Vowel signs"},
"alef.syllables": {"ru": "Чтение слогов", "en": "Reading syllables"},
"alef.dotted": {"ru": "Точка меняет звук (בּ / ב)", "en": "The dot changes the sound (בּ / ב)"},
"alef.intro": {
    "ru": "Курс алфавита. Начни с таблицы, если видишь буквы впервые.",
    "en": "The alphabet course. Start with the table if you're seeing the letters for the first time.",
},
"alef.title": {"ru": "📜 <b>Алфавит</b> (читается справа налево)",
               "en": "📜 <b>The alphabet</b> (read right to left)"},
"alef.atEnd": {"ru": "  (в конце слова: {final})", "en": "  (at the end of a word: {final})"},
"alef.dotHead": {"ru": "<b>Точка внутри буквы меняет звук</b>",
                 "en": "<b>A dot inside the letter changes the sound</b>"},
"alef.dotLine": {"ru": "<b>{shown}</b> — {name}, звук «{sound}»",
                 "en": "<b>{shown}</b> — {name}, the sound «{sound}»"},
"alef.niqqudHead": {"ru": "<b>Огласовки</b> (показаны на букве ב)",
                    "en": "<b>Vowel signs</b> (shown on the letter ב)"},
"alef.niqqudLine": {"ru": "<b>{shown}</b> — звук «{sound}»",
                    "en": "<b>{shown}</b> — the sound «{sound}»"},
"alef.finalNote": {
    "ru": "<i>Пять букв в конце слова пишутся иначе: כ→ך, מ→ם, נ→ן, פ→ף, צ→ץ.</i>",
    "en": "<i>Five letters are written differently at the end of a word: כ→ך, מ→ם, נ→ן, פ→ף, צ→ץ.</i>",
},

# ---------------------------------------------------------------- раунд
"q.counter": {"ru": "Вопрос {idx}/{total}", "en": "Question {idx}/{total}"},
"q.letters": {"ru": "Буквы: <code>{letters}</code>", "en": "Letters: <code>{letters}</code>"},
"q.anagramHint": {
    "ru": "<i>Собери из них слово. «?» — подсказка, /skip — пропустить.</i>",
    "en": "<i>Build a word from them. «?» for a hint, /skip to skip.</i>",
},
"q.typeForm": {"ru": "Напиши эту форму на иврите", "en": "Write this form in Hebrew"},
"q.typeWord": {"ru": "Напиши это слово на иврите", "en": "Write this word in Hebrew"},
"q.typeHint": {
    "ru": "<i>Огласовки писать не нужно. «?» — подсказка, /skip — пропустить.</i>",
    "en": "<i>You don't need the vowel signs. «?» for a hint, /skip to skip.</i>",
},
"q.whichForm": {"ru": "Какая это форма?", "en": "Which form is this?"},
"q.howToSay": {"ru": "Как будет «<b>{ru}</b>»?", "en": "How do you say «<b>{ru}</b>»?"},
"q.hint": {"ru": "Подсказка: <code>{hint}</code>", "en": "Hint: <code>{hint}</code>"},
"q.hintUsed": {"ru": "<i>(с подсказкой — повторим ещё раз)</i>",
               "en": "<i>(with a hint — we'll come back to it)</i>"},

"round.start": {"ru": "Начинаем! Раунд «{label}», {total} {qw}.{hint}{how}",
                "en": "Here we go. Round «{label}», {total} {qw}.{hint}{how}"},
"round.due": {"ru": " Из них на повторение: {n}.", "en": " Of those, {n} are due for review."},
"round.anagram": {"ru": " Собираешь слово из букв.", "en": " You build the word from letters."},
"round.typing": {"ru": " Пишешь ответ сам.", "en": " You type the answer yourself."},
"round.noWeak": {
    "ru": "Пока нечего повторять: ошибок слишком мало. Это хорошая новость.",
    "en": "Nothing to review yet: too few mistakes. That's good news.",
},
"round.tooSmall": {"ru": "В этой теме слишком мало слов для раунда.",
                   "en": "This topic has too few words for a round."},
"round.result": {"ru": "Итог раунда: {score}/{total} ({pct}%)",
                 "en": "Round result: {score}/{total} ({pct}%)"},
"round.again": {"ru": "{head}\n\nЖми /start, чтобы начать новый раунд.",
                "en": "{head}\n\nHit /start to begin a new round."},

# ------------------------------------------------------------ слово дня
"word.title": {"ru": "🗓 <b>Слово дня</b>", "en": "🗓 <b>Word of the day</b>"},
"word.reading": {"ru": "<i>читается: {reading}</i>", "en": "<i>reads as: {reading}</i>"},
"word.subscribe": {
    "ru": "<i>Присылать такое каждое утро — /daily_on, отключить — /daily_off.</i>",
    "en": "<i>To get this every morning — /daily_on, to stop — /daily_off.</i>",
},
"word.unsubscribe": {
    "ru": "<i>Отключить ежедневную отправку — /daily_off.</i>",
    "en": "<i>To stop the daily message — /daily_off.</i>",
},

# ----------------------------------------------------------- статистика
"stats.off": {"ru": "Статистика пока недоступна, попробуй позже.",
              "en": "Statistics aren't available right now, try again later."},
"stats.empty": {"ru": "Ты ещё не отвечал ни на один вопрос. Жми /start!",
                "en": "You haven't answered a single question yet. Hit /start!"},
"stats.title": {"ru": "📊 <b>Твоя статистика</b>", "en": "📊 <b>Your statistics</b>"},
"stats.total": {"ru": "Всего ответов: {n}", "en": "Answers in total: {n}"},
"stats.correct": {"ru": "Правильных: {n} ({pct}%)", "en": "Correct: {n} ({pct}%)"},
"stats.streak": {"ru": "Занимаешься подряд: {n} {word}",
                 "en": "Days in a row: {n} {word}"},
"stats.due": {"ru": "Ждут повторения: {n}", "en": "Due for review: {n}"},
"stats.byMode": {"ru": "<b>По режимам:</b>", "en": "<b>By section:</b>"},
"stats.weak": {"ru": "<b>Чаще всего ошибаешься:</b>", "en": "<b>Most frequent mistakes:</b>"},
"stats.weakNote": {"ru": "<i>Эти карточки бот будет показывать чаще.</i>",
                   "en": "<i>These cards will come up more often.</i>"},

# ------------------------------------------------------------ настройки
"set.dailyOn": {"ru": "Готово, буду присылать слово дня каждое утро.",
                "en": "Done — I'll send a word of the day each morning."},
"set.dailyOff": {"ru": "Больше не присылаю слово дня. Вернуть — /daily_on.",
                 "en": "No more word of the day. To bring it back — /daily_on."},
"set.voiceOn": {"ru": "Буду присылать произношение голосом.",
                "en": "I'll send the pronunciation as audio."},
"set.voiceOff": {"ru": "Голосовые отключены. Вернуть — /voice_on.",
                 "en": "Audio is off. To bring it back — /voice_on."},
"set.reactionsOn": {"ru": "Живые реплики и отметки серий включены.",
                    "en": "Live remarks and streak notes are on."},
"set.reactionsOff": {
    "ru": "Оставляю только сухие «верно / неверно». Вернуть — /reactions_on.",
    "en": "Leaving only a plain «right / wrong». To bring them back — /reactions_on.",
},
"set.slow": {"ru": "🐢 Озвучка помедленнее — легче разобрать по звукам.",
             "en": "🐢 Slower audio — easier to pick out the sounds."},
"set.normal": {"ru": "🚶 Обычная скорость озвучки.", "en": "🚶 Normal audio speed."},

# --------------------------------------------------------------- голоса
"voice.normal": {"ru": "обычная скорость", "en": "normal speed"},
"voice.slow": {"ru": "помедленнее", "en": "slower"},
"voice.missing": {
    "ru": "Образцы голосов ещё не сгенерированы.\n\n"
          "На сервере: <code>venv/bin/python3 tools/voice_samples.py</code>",
    "en": "The voice samples haven't been generated yet.\n\n"
          "On the server: <code>venv/bin/python3 tools/voice_samples.py</code>",
},
"voice.compare": {"ru": "🎧 <b>Сравнение озвучки</b>", "en": "🎧 <b>Comparing voices</b>"},
"voice.whichSpeed": {"ru": "На какой скорости прислать образцы?",
                     "en": "At which speed should I send the samples?"},
"voice.chosen": {
    "ru": "Вариант: <b>{speed}</b>. "
          "Выбранный голос вписывается в .env как <code>TTS_VOICE</code>.",
    "en": "Option: <b>{speed}</b>. "
          "The chosen voice goes into .env as <code>TTS_VOICE</code>.",
},
}
