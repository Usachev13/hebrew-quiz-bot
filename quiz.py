# -*- coding: utf-8 -*-
"""
Игровая логика: банки карточек, выбор вопроса, интервальные повторения.

Вынесено из bot.py, когда появился Mini App. Причина простая: у чата и
приложения должны быть одни правила. Если оставить подбор дистракторов и
приоритеты повторений внутри бота, приложению придётся их повторить — и
две копии начнут расходиться на первой же правке.

Здесь нет ничего от Telegram: только данные и чистые функции. Отправкой
сообщений занимается bot.py, HTTP-ответами — webapp.py.
"""

import random
from datetime import date

import alphabet
import cards
import db
import frames
import nouns
import words_en
from cards import Card
from matching import accepted_forms
from words import VOCAB, VERBS
from conjugations import (
    CONJUGATIONS,
    PAST_PERSONS, PAST_LABELS,
    PRESENT_SLOTS, PRESENT_LABELS,
    FUTURE_SLOTS, FUTURE_LABELS,
)

ROUND_LEN = 10

# Анаграмму предлагаем только там, где собирать слово из букв осмысленно:
# длинная глагольная форма разбирается на пятнадцать букв и учит терпению,
# а не языку.
ANAGRAM_MODES = {"vocab", "weak"}


def flatten(bank, en=None):
    """Превращает {категория: [(ru, he), ...]} в плоский список карточек.

    `en` — словарь переводов подсказки, ключ `cid`. Отсутствующий перевод
    не ошибка на этом уровне: карточка просто останется с русской
    подсказкой, а недостачу поимённо назовёт tools/check_i18n.py. Падать
    здесь нельзя — импорт quiz.py поднимает и бота, и приложение.
    """
    en = en or {}
    items = []
    for category, words in bank.items():
        for ru, he in words:
            cid = cards.vocab_cid(category, he)
            items.append(Card(ru, he, category, cid=cid, en=en.get(cid, "")))
    return items


def flatten_tense(conj, tense, slots, labels, en_labels=None):
    """Одно время из CONJUGATIONS -> плоский список (подсказка, форма, группа).

    Группа = глагол+время: дистракторы берутся из форм ТОГО ЖЕ глагола в
    том же времени, поэтому тренируется именно лицо/род/число, а не
    угадывание по внешнему виду разных корней."""
    en_labels = en_labels or {}
    items = []
    for root, data in conj.items():
        for slot in slots:
            he = data[tense].get(slot)
            if not he:
                continue
            prompt = f"{data['ru']} ({data['inf']}) — {labels[slot]}"
            meaning = words_en.ROOT_MEANINGS.get(root)
            label_en = en_labels.get(slot)
            en = f"{meaning} ({data['inf']}) — {label_en}" if meaning and label_en else ""
            items.append(Card(prompt, he, f"{root}_{tense}",
                              cid=cards.form_cid(root, slot), en=en))
    return items


def plural_cards():
    """«один — много»: показываем единственное, спрашиваем множественное.

    Берём только те слова, у которых множественное вообще есть: у «хлеба»
    и «соли» его в обиходе нет, и спрашивать о нём — учить тому, чего не
    говорят. Список размечен в nouns.py.
    """
    out = []
    for c in VOCAB_FLAT:
        pl = nouns.plural_of(c.he)
        if not pl:
            continue
        # Подпись как у форм глагола: «писать (לִכְתּוֹב) — я».
        # Единственное показываем на иврите — его и надо преобразовать,
        # а перевод нужен, чтобы человек понимал, о чём речь.
        out.append(Card(
            # «— много», а не «— множественное число», стояло сначала.
            # Подпись неточная: формы на ־ַיִם исторически двойственные,
            # но «ידיים» сегодня значит и «руки» вообще, а не ровно две.
            # «Много» обещает количество, которого форма не несёт.
            ru=f"{c.ru} ({c.he}) — множественное число",
            he=pl,
            cat=c.cat,
            cid=f"plural:{c.cid}",
            en=f"{c.en} ({c.he}) — plural" if c.en else "",
        ))
    return out


GAP_FLAT = frames.verb_cards(words_en.ROOT_MEANINGS)
WHO_FLAT = frames.who_cards(words_en.ROOT_MEANINGS)

VOCAB_FLAT = flatten(VOCAB, words_en.WORDS)
VERBS_FLAT = flatten(VERBS, words_en.VERBS)
PLURAL_FLAT = plural_cards()
PAST_FLAT = flatten_tense(CONJUGATIONS, "past", PAST_PERSONS, PAST_LABELS,
                          words_en.PAST_LABELS)
PRESENT_FLAT = flatten_tense(CONJUGATIONS, "present", PRESENT_SLOTS, PRESENT_LABELS,
                             words_en.PRESENT_LABELS)
FUTURE_FLAT = flatten_tense(CONJUGATIONS, "future", FUTURE_SLOTS, FUTURE_LABELS,
                            words_en.FUTURE_LABELS)


def pick_card(remaining, priorities, rng=random):
    """Выбирает следующую карточку с учётом интервальных повторений.

    Берём случайную из самой приоритетной группы (см. db.PRIORITY_*):
    сперва то, что пора повторить, затем новое, затем проблемное. Внутри
    группы порядок случайный — чтобы не заучивать последовательность.

    `rng` нужен там, где случайность вредна. В раунде она на месте: два
    подхода подряд не должны идти одним и тем же порядком. А карточка
    «Продолжить» на главной — обещание, а не жребий: она показывает, с
    чего начнётся занятие, и меняться от нажатия на «Главная» не должна.
    Туда передаётся жребий, засеянный днём и человеком.
    """
    if not priorities:
        return rng.choice(remaining)
    rank = lambda w: priorities.get(w.key(), db.PRIORITY_NEW)
    best = max(rank(w) for w in remaining)
    return rng.choice([w for w in remaining if rank(w) == best])


def daily_rng(chat_id):
    """Жребий, одинаковый для человека в течение суток.

    Один посев на главный экран и на слово дня: оба должны стоять на
    месте, пока человек ходит по вкладкам.
    """
    return random.Random(f"{chat_id}:{date.today().isoformat()}")


INTRO_LEN = 6      # сколько новых слов показываем перед викториной
MIN_ROUND = 5      # короче этого раунд не имеет смысла запускать


def intro_cards(chat_id, mode, pool):
    """Карточки из пула, которых пользователь ещё ни разу не видел.

    До этого приложение сразу спрашивало слово, которого человек не
    встречал: викторина превращалась в угадайку, а первая коробка
    интервального повторения наполнялась случайными промахами. Сначала
    знакомство, потом вопрос.
    """
    if mode == "weak":
        return []                      # слабые места по определению уже видели
    try:
        seen = db.seen_cards(chat_id, mode)
    except Exception as e:
        print(f"[intro_cards] БД недоступна: {e}")
        return []
    fresh = [w for w in pool if w.key() not in seen]
    random.shuffle(fresh)
    return fresh[:INTRO_LEN]


def build_question(pool, used, priorities=None, pick_from=None, lang="ru",
                   flip=False):
    """Выбирает карточку (ещё не заданную в этом раунде) и 3 дистрактора
    из той же категории/группы биньяна — так угадать наугад сложнее.

    pick_from сужает выбор самой карточки, не трогая дистракторы: после
    знакомства спрашиваем ровно те слова, которые только что показали, а
    неверные варианты по-прежнему берём из всей темы — иначе они были бы
    только из шести новых и ответ вычислялся бы по исключению.

    flip переворачивает вопрос: варианты собираются со стороны подсказки,
    а не ответа. Нужно для аудирования — там человек слышит иврит и
    выбирает перевод, то есть отвечает по-русски.
    """
    side = (lambda w: w.prompt(lang)) if flip else (lambda w: w.answer(lang))
    source = pick_from if pick_from else pool
    remaining = [w for w in source if w.key() not in used]
    if not remaining:
        remaining = source
    correct = pick_card(remaining, priorities or {})
    answer = side(correct)

    # Дистракторы обязаны отличаться не только от верного ответа, но и
    # друг от друга: в некоторых пулах разные карточки дают одинаковый
    # ответ (патах и камац оба читаются как «а»), и без этой проверки в
    # вопросе появлялись два одинаковых варианта.
    seen = {answer}

    # Карточка сама принесла неверные варианты — брать из пула нечего.
    # См. quiz.syntax_cards(): там дистрактор обязан отличаться от
    # верного ответа ровно одним нарушенным правилом.
    if correct.wrong:
        options = [answer] + list(correct.wrong)
        random.shuffle(options)
        return {"id": correct.key(), "ru": correct.prompt(lang),
                "correct": answer, "options": options, "voice": None}

    def take(candidates, need):
        random.shuffle(candidates)
        for w in candidates:
            if len(seen) > need:
                break
            if side(w) not in seen:
                seen.add(side(w))

    take([w for w in pool if w.cat == correct.cat], 3)   # сначала из той же темы
    take([w for w in pool if w.cat != correct.cat], 3)   # не хватило — из любой

    options = list(seen)
    random.shuffle(options)
    # В перевёрнутом вопросе показывать нечего: задание — это звук.
    # Ивритский текст отдаём отдельным полем, чтобы по нему нашли файл
    # озвучки, а на экран он не попал.
    return {"id": correct.key(), "ru": "" if flip else correct.prompt(lang),
            "correct": answer, "options": options,
            "voice": correct.he if flip else None}


def abbrev_cards():
    """Аббревиатура -> расшифровка.

    Вопрос ставим в ту сторону, в какую он встаёт в жизни: человек видит
    `ת"ז` на бланке и должен понять, что это. Перевод и место, где это
    попадается, уходят в разбор — иначе подсказка была бы в самом
    вопросе.
    """
    import abbrev
    out = []
    for a, full, ru, _where, _src in abbrev.all_items():
        out.append(Card(ru=f"{a} — что это?", he=full, cat="abbrev",
                        cid=f"abbrev:{a}",
                        en=f"{a} — what is it?"))
    return out


ABBREV_FLAT = abbrev_cards()


def syntax_cards():
    """«Собери фразу»: варианты ответа — искажения ЭТОЙ ЖЕ фразы.

    Обычный дистрактор здесь не работает. Если к «בַּיִת גָּדוֹל» подставить
    три случайные фразы из пула, человек выберет верную по знакомым
    словам и ничего не узнает о порядке слов. Поэтому неверные варианты
    заданы в syntax.py рядом с правилом, которое каждый из них нарушает,
    и кладутся в саму карточку.

    Ключ карточки содержит род говорящего только там, где ответ от него
    зависит (אֲנִי רוֹאֶה / רוֹאָה). В остальных каркасах фраза одна для
    всех, и прогресс не должен раздваиваться.
    """
    import syntax
    out = []
    for i, (ru, en, right, wrongs, frame) in enumerate(syntax.SENTENCES):
        out.append(Card(ru=ru, he=right, cat=frame,
                        cid=f"syntax:{frame}:{i}", en=en,
                        wrong=tuple(w for w, _rule in wrongs)))
    return out


def preposition_cards():
    """Склонение предлогов: לִי, שֶׁלִּי, אִתִּי.

    Без этих форм нельзя сказать почти ничего: «у меня есть» — это
    יֵשׁ לִי, «моя книга» — הַסֵּפֶר שֶׁלִּי. Данные размечены давно (пять
    предлогов со всеми формами), а тренировать их было негде.

    Дистракторы берутся из форм ТОГО ЖЕ предлога — так же, как у
    глагольных форм. Иначе выбор шёл бы по внешнему виду: «что-то на
    шин» против «что-то на алеф», и человек угадывал бы предлог, не
    вспоминая лицо.
    """
    import hebrew_meta
    out = []
    for key, data in hebrew_meta.PREPOSITIONS.items():
        forms = data["forms"]
        for i, form in enumerate(forms):
            if i >= len(hebrew_meta.PERSONS):
                break
            ru, en = hebrew_meta.PERSONS[i], hebrew_meta.PERSONS_EN[i]
            out.append(Card(
                ru=f"{data['base']} ({data['ru'].split(' — ')[0]}) — {ru}",
                he=form,
                cat=f"prep_{key}",
                cid=f"prep:{key}:{i}",
                en=f"{data['base']} ({data['en'].split(' — ')[0]}) — {en}",
            ))
    return out


PREP_FLAT = preposition_cards()


def numeral_cards():
    """«Сколько чего»: форма числа под род существительного.

    Берём только те слова, у которых род и множественное подтверждены
    словарём, — то есть ровно те, что уже работают в «один и много».
    """
    import numerals
    pairs = [(c.he, c.ru, nouns.gender_of(c.he), nouns.plural_of(c.he))
             for c in VOCAB_FLAT if nouns.plural_of(c.he)]
    rows = numerals.cards(pairs) + numerals.two_cards(pairs)
    out = []
    for i, (ru, en, right, wrongs, frame) in enumerate(rows):
        out.append(Card(ru=ru, he=right, cat=frame,
                        cid=f"numerals:{frame}:{i}", en=en,
                        wrong=tuple(w for w, _r in wrongs)))
    return out


NUMERALS_FLAT = numeral_cards()

SYNTAX_FLAT = syntax_cards()
SYNTAX_MODES = {"syntax"}


def syntax_pool(female):
    """Фразы «собери фразу» для одного рода говорящего."""
    skip = "et_m_sg" if female else "et_f_sg"
    return [c for c in SYNTAX_FLAT if c.cat != skip]

POOLS = {
    "vocab": VOCAB_FLAT,
    "verbs": VERBS_FLAT,
    "past": PAST_FLAT,
    "present": PRESENT_FLAT,
    "future": FUTURE_FLAT,
    # Фразы с пропуском. Отличие от трёх режимов выше не в оформлении:
    # там лицо и время названы прямо («писать — я»), здесь спрятаны в
    # самой фразе, и их надо услышать. См. frames.py.
    "gap_verb": GAP_FLAT,
    "gap_who": WHO_FLAT,
    "plural": PLURAL_FLAT,
    "abbrev": ABBREV_FLAT,
    "syntax": SYNTAX_FLAT,
    "numerals": NUMERALS_FLAT,
    "prepositions": PREP_FLAT,
    # Курс алфавита (уровень 0)
    "alef_names": alphabet.pool_names(),
    "alef_sounds": alphabet.pool_sounds(),
    "alef_by_name": alphabet.pool_by_name(),
    "alef_finals": alphabet.pool_finals(),
    "alef_niqqud": alphabet.pool_niqqud(),
    "alef_syllables": alphabet.pool_syllables(),
    "alef_dotted": alphabet.pool_dotted(),
}
LABELS = {
    "vocab": "слова",
    "verbs": "глаголы",
    "past": "прошедшее время",
    "present": "настоящее время",
    "future": "будущее время",
    "gap_verb": "поставь глагол во фразу",
    "gap_who": "кто это делает",
    "plural": "один и много",
    "abbrev": "сокращения",
    "syntax": "собери фразу",
    "numerals": "сколько чего",
    "prepositions": "предлоги с местоимениями",
    "listen": "на слух",
    "sprint": "спринт",
    "alef_names": "названия букв",
    "alef_sounds": "звуки букв",
    "alef_by_name": "узнать букву по названию",
    "alef_finals": "конечные формы",
    "alef_niqqud": "огласовки",
    "alef_syllables": "чтение слогов",
    "alef_dotted": "точка меняет звук",
}

# Словарь разложен по двум разрезам. Бытовые темы — как в ульпане:
# человек учит слова кусками жизни, а не списком существительных.
# Грамматические группы вынесены отдельно, потому что тренируются иначе:
# там важна не тема, а форма.
TOPIC_LABELS = {
    "greetings": "Приветствия", "family": "Семья", "food": "Еда",
    "home": "Дом", "city": "Город", "transport": "Транспорт",
    "time": "Время", "weather": "Погода", "health": "Здоровье",
    "shopping": "Покупки", "work_study": "Работа и учёба",
    "clothes": "Одежда", "emotions": "Эмоции",
}
GRAMMAR_LABELS = {
    "adjectives": "Прилагательные", "adverbs": "Наречия",
    "personal_pronouns": "Местоимения (я, ты…)",
    "object_pronouns": "Местоимения (меня, его…)",
    "cardinals": "Числительные", "ordinals": "Порядковые",
    "question_words": "Вопросительные слова", "particles": "Частицы",
    "place_prepositions": "Предлоги места",
}

# Те же подписи по-английски. Держим рядом с русскими, а не в общем
# словаре интерфейса: это названия разделов учебного материала, они
# меняются вместе с самим материалом, а не с оформлением приложения.
LABELS_EN = {
    "vocab": "words",
    "verbs": "verbs",
    "past": "past tense",
    "present": "present tense",
    "future": "future tense",
    "gap_verb": "put the verb into the sentence",
    "gap_who": "who is doing it",
    "plural": "one and many",
    "abbrev": "abbreviations",
    "syntax": "build the sentence",
    "numerals": "how many of what",
    "prepositions": "prepositions with pronouns",
    "listen": "by ear",
    "sprint": "sprint",
    "alef_names": "letter names",
    "alef_sounds": "letter sounds",
    "alef_by_name": "find the letter by name",
    "alef_finals": "final forms",
    "alef_niqqud": "vowel signs",
    "alef_syllables": "reading syllables",
    "alef_dotted": "the dot changes the sound",
}
TOPIC_LABELS_EN = {
    "greetings": "Greetings", "family": "Family", "food": "Food",
    "home": "Home", "city": "City", "transport": "Transport",
    "time": "Time", "weather": "Weather", "health": "Health",
    "shopping": "Shopping", "work_study": "Work and study",
    "clothes": "Clothes", "emotions": "Emotions",
}
GRAMMAR_LABELS_EN = {
    "adjectives": "Adjectives", "adverbs": "Adverbs",
    "personal_pronouns": "Pronouns (I, you…)",
    "object_pronouns": "Pronouns (me, him…)",
    "cardinals": "Numbers", "ordinals": "Ordinal numbers",
    "question_words": "Question words", "particles": "Particles",
    "place_prepositions": "Prepositions of place",
}

WEAK_LABEL = {"ru": "мои слабые места", "en": "my weak spots"}


def section_label(mode, cat=None, lang="ru"):
    """Название раздела: тема, если она задана, иначе сам режим.

    Возвращает None, когда режим неизвестен: вызывающий по этому
    отличает «нечего продолжать» от пустой строки.
    """
    if lang == "en":
        topics, grammar, modes = TOPIC_LABELS_EN, GRAMMAR_LABELS_EN, LABELS_EN
    else:
        topics, grammar, modes = TOPIC_LABELS, GRAMMAR_LABELS, LABELS
    if mode == "weak":
        return WEAK_LABEL.get(lang, WEAK_LABEL["ru"])
    if cat:
        return topics.get(cat) or grammar.get(cat) or modes.get(mode)
    return modes.get(mode)

# Режимы с пропуском: подсказка уже сама себе вопрос («אֶתְמוֹל אֲנִי ___»),
# спрашивать сверху «как будет…» нечего.
# Раздел «Грамматика» в приложении: темы словаря плюс режимы, которые
# темой не являются. Список лежит здесь, а не в webapp, чтобы проверка
# страницы могла сверить его с набросками плиток: ключ плитки и id
# рисунка обязаны совпасть, а найти расхождение в браузере я не могу.
GRAMMAR_SECTIONS = ([(key, None) for key in GRAMMAR_LABELS]
                    + [("plural", "plural"), ("abbrev", "abbrev"),
                       ("syntax", "syntax"), ("numerals", "numerals"),
                       ("prepositions", "prepositions")])

GAP_MODES = {"gap_verb", "gap_who"}

# Приставка в поле «категория», означающая «глаголы такого-то биньяна».
# Своя форма нужна потому, что обычная категория у форм — «корень_время»,
# и по ней биньян не отберёшь.
BINYAN_PREFIX = "binyan:"

# Режимы курса алфавита: вопрос формулируется иначе, чем «как будет…»
# Режимы, где транскрипцию показывать нельзя. У сокращений расшифровка
# написана без огласовок — нарочно, так она и выглядит в жизни, — а наше
# чтение по неогласованному тексту выдаёт «твдт зхвт». Лучше ничего.
# Аудирование: слышишь слово — выбираешь перевод. Пул собирается на
# лету, потому что зависит от наличия файлов озвучки: слово без записи
# спросить нечем. Поэтому в POOLS его нет — там статические наборы.
# Спринт на время. Отдельный ключ режима, а не «vocab на скорость»:
# ответы в спешке не должны править расписание повторений. Человек
# промахивается по кнопке, а Лейтнер понимает это как «забыл слово» и
# вытаскивает его заново — наказание за игру.
SPRINT_MODES = {"sprint"}
SPRINT_SECONDS = 60
# Вопросов в выдаче заведомо больше, чем успевает любой: за минуту это
# примерно двадцать, а отдаём сорок, чтобы раунд не кончился раньше
# времени.
SPRINT_QUESTIONS = 40

LISTEN_MODES = {"listen"}


def listen_pool():
    """Словарные карточки, у которых есть озвучка."""
    import audio
    return [c for c in VOCAB_FLAT if audio.has_audio(c.he)]


NO_READING_MODES = {"abbrev"}

ALPHABET_MODES = {m for m in LABELS if m.startswith("alef_")}

# Порядок прохождения — от узнавания к чтению. Раньше разделы шли по
# алфавиту внутреннего ключа: «узнать букву по названию» оказывалось
# первым, а «названия букв» четвёртым, хотя без вторых первое
# бессмысленно. Теперь разделы ещё и нумеруются буквами в приложении,
# и случайный порядок стал бы прямой дезинформацией.
ALPHABET_ORDER = (
    "alef_names",      # как называется буква
    "alef_sounds",     # какой звук она даёт
    "alef_by_name",    # обратный ход: узнать букву по названию
    "alef_finals",     # конечные формы
    "alef_dotted",     # дагеш меняет звук
    "alef_niqqud",     # огласовки
    "alef_syllables",  # и только теперь — чтение слогов
)
assert set(ALPHABET_ORDER) == ALPHABET_MODES, "порядок разошёлся с режимами"

# Обратный поиск: по ключу карточки найти её саму. Нужен и проверке
# ответа, и статистике: список слабых мест без ивритского слова только
# перечисляет промахи, а с карточкой — повторяет материал.
#
# Раньше здесь лежала пара (ответ, категория), а ключом была русская
# подсказка. Теперь ключ устойчивый, а значение — вся карточка: ответ у
# алфавита зависит от языка («алеф» или «alef»), и обрезанное значение
# пришлось бы доставать заново.
ANSWERS = {mode: {c.key(): c for c in pool} for mode, pool in POOLS.items()}

# Тот же поиск по ПОДСКАЗКЕ, а не по ключу. Нужен на время перехода:
# старая версия приложения присылает обратно текст вопроса, потому что
# раньше он и был ключом. Пока у людей в телефонах живёт та версия,
# ответы должны доходить.
#
# Английские подсказки здесь обязательны, и это не запас на будущее.
# Язык определяется из настроек Telegram сразу после выкладки: человек с
# английским телефоном получит вопрос «bread» ещё старым приложением и
# пришлёт обратно именно «bread». Без этой строки его ответ вернулся бы
# ошибкой «unknown card», и раунд встал бы намертво.
LEGACY_ANSWERS = {
    mode: {p: c for c in pool for p in (c.ru, c.en) if p}
    for mode, pool in POOLS.items()
}


def find_card(mode, card_id):
    """Карточка по ключу — новому или старому.

    Аудирование и спринт работают на словарных карточках: своих наборов у
    них нет. Поэтому ключ ищем среди словарных, иначе ответ не с чем
    сверить.
    """
    look = "vocab" if mode in LISTEN_MODES | SPRINT_MODES else mode
    by_mode = ANSWERS.get(look, {})
    return by_mode.get(card_id) or LEGACY_ANSWERS.get(look, {}).get(card_id)


def id_migration_map():
    """{режим: {старая русская подсказка: новый ключ}} для db.migrate_card_ids.

    Старый ключ — ровно то, что раньше клалось в базу: `Card.ru`. Новый
    лежит в `cid`. Пары строятся из тех же карточек, что показываются
    сейчас, поэтому карта не может разойтись с данными: слово, которого
    в словаре больше нет, и переносить некуда.
    """
    return {mode: {c.ru: c.cid for c in pool if c.cid and c.cid != c.ru}
            for mode, pool in POOLS.items()}


# Все допустимые написания каждого пула. Нужны, чтобы отличить описку от
# случая «набрал другое существующее слово» (см. matching.check_answer).
# Берём ивритское поле, а не язык интерфейса: набором проверяются только
# словарь и глаголы, где ответ на иврите при любом языке.
KNOWN_FORMS = {
    mode: set().union(*(accepted_forms(c.he) for c in pool)) if pool else set()
    for mode, pool in POOLS.items()
}
# Раунд «слабые места» смешанный, поэтому описку в нём сверяем по всему
# банку сразу: иначе набранное слово из другого режима сойдёт за опечатку.
KNOWN_FORMS["weak"] = set().union(*KNOWN_FORMS.values())


def weak_pool(chat_id, limit=30):
    """Карточки, где больше всего ошибок — со всех режимов сразу.

    Возвращает (пул, {(подсказка, ответ): режим}). Режим на карточку
    нужен потому, что раунд смешанный: ответ должен лечь в статистику
    того режима, откуда карточка пришла, иначе повторения разъедутся.
    """
    try:
        weak = db.weak_cards(chat_id, limit=limit)
    except Exception as e:
        print(f"[weak_pool] {e}")
        return [], {}

    pool, modes = [], {}
    for w in weak:
        card = ANSWERS.get(w["mode"], {}).get(w["card_id"])
        if not card:
            continue          # карточка из старой версии словаря
        pool.append(card)
        modes[card.key()] = w["mode"]
    return pool, modes


def round_pool(chat_id, mode, cat, lang="ru"):
    """Пул раунда, подпись к нему и карта режимов по карточкам."""
    if mode == "weak":
        pool, modes = weak_pool(chat_id)
        return pool, section_label("weak", lang=lang), modes

    if mode in SYNTAX_MODES:
        # Фразы от первого лица зависят от рода говорящего: «אֲנִי רוֹאֶה»
        # для мужчины, «רוֹאָה» для женщины. Показать оба набора значило
        # бы объявить верную форму неверной через карточку. Пол уже
        # спрошен и пропустить его нельзя (см. задачу про выбор пола).
        pool = syntax_pool(db.gender(chat_id) == "f")
        if cat:
            pool = [w for w in pool if w.cat == cat]
        return pool, section_label(mode, lang=lang), {}

    if mode in LISTEN_MODES:
        pool = listen_pool()
        if cat:
            pool = [w for w in pool if w.cat == cat]
        return pool, section_label(mode, lang=lang), {}

    pool = POOLS[mode]
    if cat and cat.startswith(BINYAN_PREFIX):
        # Тренировка одного биньяна: вход со страницы грамматики.
        # Прочитал, как устроен пиэль, — и тут же прогнал только его
        # глаголы. Без этого страница остаётся чтением, после которого
        # человек возвращается к перемешанному списку и ничего не
        # закрепляет.
        import grammar
        roots = set(grammar.verbs_of(cat[len(BINYAN_PREFIX):]))
        pool = [w for w in pool if w.cat.rsplit("_", 1)[0] in roots]
        page = grammar.page(cat[len(BINYAN_PREFIX):], lang)
        return pool, (page["title"] if page else section_label(mode, lang=lang)), {}
    if cat:
        pool = [w for w in pool if w.cat == cat]
        return pool, section_label(mode, cat, lang).lower(), {}
    return pool, section_label(mode, lang=lang), {}


# ---------- слово дня ----------

def pick_daily_word(chat_id, today=None):
    """Слово дня. По очереди, от самого желанного к запасному варианту:

    1. не приходило как слово дня и ещё не встречалось в раундах — новое;
    2. не приходило как слово дня, хоть и встречалось — напоминание;
    3. приходило дольше всех остальных — круг пошёл заново.

    Важен первый фильтр. Отбор только по «не встречалось в раундах» не
    годится: этот запас тает по мере учёбы, и на 272 отвеченных словах из
    273 выбор сужается до одного — оно и приходит каждый день.

    Одно слово на весь день
    -----------------------
    Выбор ОБЯЗАН быть одинаковым при каждом вызове в течение суток. Это
    не оптимизация, а смысл названия: «слово дня», которое меняется от
    того, что человек нажал «Главная», — просто случайное слово.

    Раньше здесь стоял random.choice, и приложение перерисовывало слово
    на каждом открытии экрана. Хуже того, после утренней рассылки бот и
    приложение расходились: отправленное слово попадало в `sent` и тем
    самым ВЫБЫВАЛО из выбора, так что в чате человек видел одно, а в
    приложении другое.

    Поэтому: сперва смотрим, не отправляли ли уже сегодня — тогда это
    оно и есть. Если нет, тянем жребий, засеянный парой «кто + какой
    сегодня день». Один и тот же посев даёт один и тот же ответ, сколько
    ни спрашивай, и записывать ничего не нужно — приложение не должно
    менять данные только оттого, что его открыли.
    """
    today = today or date.today().isoformat()
    try:
        seen = db.seen_cards(chat_id, "vocab")
        sent = db.daily_sent_words(chat_id)
    except Exception as e:
        print(f"[pick_daily_word] БД недоступна: {e}")
        # Без базы жребий всё равно держим устойчивым: лучше показать
        # одно и то же слово, чем мелькать разными.
        return random.Random(f"{chat_id}:{today}").choice(VOCAB_FLAT)

    # Уже присылали сегодня — показываем ровно его, иначе чат и
    # приложение скажут человеку разное.
    for cid, day in sent.items():
        if day == today:
            card = ANSWERS["vocab"].get(cid)
            if card:
                return card

    rng = random.Random(f"{chat_id}:{today}")
    never_sent = [w for w in VOCAB_FLAT if w.key() not in sent]
    unseen = [w for w in never_sent if w.key() not in seen]
    if unseen:
        return rng.choice(unseen)
    if never_sent:
        return rng.choice(never_sent)

    oldest = min(sent.values())
    return rng.choice([w for w in VOCAB_FLAT if sent.get(w.key()) == oldest])
