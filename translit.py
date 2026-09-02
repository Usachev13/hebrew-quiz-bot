# -*- coding: utf-8 -*-
"""
Произношение кириллицей — выводится из огласовок автоматически.

Руками транслитерацию для ~1900 карточек не набрать, но она и не нужна:
у нас всюду проставлены огласовки, а они однозначно задают чтение.
Поэтому произношение строится по тем же правилам, что и спряжения.

Точность: передаём звучание так, как его слышит русскоязычный.

В кириллице ударение не отмечаем — она нужна, чтобы прочитать слово.
А вот для синтезатора ударение обязательно (см. to_ipa ниже): сам он
ставит его по общему правилу и ошибается на целом классе слов.
"""

import unicodedata

DAGESH = "ּ"
SHIN_DOT = "ׁ"
SIN_DOT = "ׂ"

# Огласовки -> звук. Патах и камац в современном иврите звучат одинаково.
VOWELS = {
    "ַ": "а",   # патах
    "ָ": "а",   # камац
    "ֶ": "е",   # сеголь
    "ֵ": "е",   # цере
    "ִ": "и",   # хирик
    "ֹ": "о",   # холам
    "ֻ": "у",   # кубуц
    "ֲ": "а",   # хатаф-патах
    "ֱ": "е",   # хатаф-сеголь
    "ֳ": "о",   # хатаф-камац
}
SHVA = "ְ"
KAMATS = "ָ"
HATAF_KAMATS = "ֳ"

# «Камац катан» — камац, который читается как «о», а не «а»
# (כָּל = коль, צָהֳרַיִם = цохорайим). Формально это камац в закрытом
# безударном слоге, но надёжно вывести это из одних огласовок нельзя:
# нужна информация об ударении, которой у нас нет. На весь наш банк
# таких слов ровно два, поэтому — одно правило и один список.
#
# Правило: камац перед буквой с хатаф-камацем — всегда катан.
# Список: слова, которые под правило не подпадают.
KAMATS_KATAN_WORDS = {"כָּל"}

# Согласные. Для ב, כ, פ звук зависит от дагеша, для ש — от точки сбоку.
CONSONANTS = {
    "א": "", "ב": "в", "ג": "г", "ד": "д", "ה": "х", "ו": "в", "ז": "з",
    "ח": "х", "ט": "т", "י": "й", "כ": "х", "ך": "х", "ל": "л", "מ": "м",
    "ם": "м", "נ": "н", "ן": "н", "ס": "с", "ע": "", "פ": "ф", "ף": "ф",
    "צ": "ц", "ץ": "ц", "ק": "к", "ר": "р", "ש": "ш", "ת": "т",
}
# С дагешем эти три читаются иначе
HARD = {"ב": "б", "כ": "к", "פ": "п"}


def _split(word):
    """Разбивает слово на пары (буква, значки при ней)."""
    out = []
    for ch in unicodedata.normalize("NFC", word or ""):
        if unicodedata.combining(ch):
            if out:
                out[-1][1].append(ch)
        elif ch == " ":
            out.append([" ", []])
        else:
            out.append([ch, []])
    return out


# --- IPA: транскрипция для синтезатора ---
#
# Синтезатор сам ударение не угадывает (говорит «бокЕр» вместо «бОкер»),
# но принимает подсказку в IPA. Расписывать транскрипцию для 1884
# карточек руками нереально, поэтому строим её из огласовок — тем же
# разбором, что и произношение кириллицей.

IPA_CONSONANTS = {
    "א": "", "ב": "v", "ג": "ɡ", "ד": "d", "ה": "h", "ו": "v", "ז": "z",
    "ח": "χ", "ט": "t", "י": "j", "כ": "χ", "ך": "χ", "ל": "l", "מ": "m",
    "ם": "m", "נ": "n", "ן": "n", "ס": "s", "ע": "", "פ": "f", "ף": "f",
    "צ": "ts", "ץ": "ts", "ק": "k", "ר": "ʁ", "ש": "ʃ", "ת": "t",
}
IPA_HARD = {"ב": "b", "כ": "k", "פ": "p"}
IPA_VOWELS = {"а": "a", "е": "e", "и": "i", "о": "o", "у": "u"}


# Слова, где ударение не выводится из огласовок правилами ниже.
# Пополняется по мере находок на слух — в огласовках ударения нет,
# и вывести его в общем виде невозможно.
#
# milel — ударение на предпоследнем слоге, milra — на последнем.
STRESS_EXCEPTIONS = {
    "לָמָּה": "milel",      # ЛА-ма, а не ла-МА
}


def _stress_exception(word):
    return STRESS_EXCEPTIONS.get(unicodedata.normalize("NFC", word or ""))


def _verb_ending_stress(units):
    """Ударение по глагольному окончанию прошедшего времени.

    В прошедшем времени ударение зависит от лица, а не от вида слова:
        כָּתַבְתִּי — ка-ТАВ-ти      (-ти  тянет ударение назад)
        כָּתַבְתָּ  — ка-ТАВ-та      (-та  тоже)
        כָּתַבְנוּ — ка-ТАВ-ну      (-ну  тоже)
        כְּתַבְתֶּם — кта-в-ТЕМ      (-тем оставляет на последнем)
        כָּתַב     — ка-ТАВ         (без окончания — на последнем)

    Возвращает True (предпоследний слог), False (последний) или None,
    если окончание ни о чём не говорит и надо смотреть дальше.
    """
    letters = [(l, m) for l, m in units if l != " "]
    if len(letters) < 3:
        return None

    last, last_marks = letters[-1]
    prev, prev_marks = letters[-2]

    # ...תִּי — «я»
    if last == "י" and prev == "ת" and "ִ" in prev_marks:
        return True
    # ...נוּ — «мы»
    if last == "ו" and DAGESH in last_marks and prev == "נ":
        return True
    # ...תָּ — «ты (муж.)»
    if last == "ת" and KAMATS in last_marks:
        return True
    # ...תֶּם / ...תֶּן — «вы»: ударение остаётся на последнем слоге,
    # хотя по виду слова сработало бы правило сеголатных
    if last in ("ם", "ן") and prev == "ת" and "ֶ" in prev_marks:
        return False

    return None


def _is_segolate(units):
    """Слово с ударением на предпоследнем слоге.

    В иврите ударение обычно на последнем слоге, но у «сеголатных» слов
    (בֹּקֶר, לֶחֶם, כֶּסֶף) — на предпоследнем. Признак: последняя гласная —
    сеголь, и слово не оканчивается на ה (иначе это מוֹרֶה, где ударение
    как раз на последнем).

    Отдельно — «патах гнува» под конечными ע/ח: תַּפּוּחַ читается «тапУах»,
    ударение тоже смещено.
    """
    letters = [(l, m) for l, m in units if l != " "]
    if len(letters) < 2:
        return False

    last_letter, last_marks = letters[-1]
    if last_letter in "עח" and "ַ" in last_marks:
        return True
    if last_letter == "ה":
        return False

    # ищем последнюю гласную в слове
    for letter, marks in reversed(letters):
        vowel = next((m for m in marks if m in VOWELS), None)
        if vowel:
            return vowel == "ֶ"
    return False


HIRIQ = "ִ"


def _helping_hiriq(units):
    """Слово вида בַּיִת / מַיִם / ־ַיִם — ударение на предпоследнем слоге.

    Хирик под йодом здесь не настоящая гласная, а вставка для
    произносимости — ровно как сеголь у сеголатных. Слог «-йи-» ударение
    не притягивает: БÁйит, МÁйим, шамÁйим, цохорÁйим, меÁйин.
    Сюда же попадает всё двойственное число на ־ַיִם (יָדַיִם, נַעֲלַיִם,
    מִשְׁקָפַיִם) — оно всегда так и звучит.

    Отличать надо от תִּהְיִי «тихйИ», где хирик настоящий: там слово
    кончается на йод-мать чтения, а не на согласную.
    """
    letters = [(l, m) for l, m in units if l != " "]
    if len(letters) < 3:
        return False

    last, last_marks = letters[-1]
    prev, prev_marks = letters[-2]
    if prev != "י" or HIRIQ not in prev_marks:
        return False
    # последняя буква должна закрывать слог настоящей согласной
    if last in ("י", "ו", "ה") or any(m in VOWELS for m in last_marks):
        return False
    # перед йодом стоит гласная — иначе вставки не было бы
    return any(m in VOWELS for m in letters[-3][1])


def to_ipa(word):
    """Транскрипция слова в IPA с ударением."""
    if " " in (word or ""):
        return " ".join(to_ipa(w) for w in word.split())

    units = _split(word)
    syllables = []          # список слогов
    current = ""            # накапливаемый слог
    prev_was_vocal_shva = False

    for i, (letter, marks) in enumerate(units):
        if letter not in CONSONANTS:
            continue

        vowel = next((VOWELS[m] for m in marks if m in VOWELS), None)
        if KAMATS in marks:
            nxt_marks = units[i + 1][1] if i + 1 < len(units) else []
            if unicodedata.normalize("NFC", word) in KAMATS_KATAN_WORDS \
                    or HATAF_KAMATS in nxt_marks:
                vowel = "о"

        has_dagesh = DAGESH in marks
        prev_marks = units[i - 1][1] if i > 0 else []
        nxt = units[i + 1] if i + 1 < len(units) else None

        # ו и י бывают частью гласной, а не согласными
        if letter == "ו":
            if has_dagesh and vowel is None:
                current += "u"
                syllables.append(current); current = ""
                continue
            if vowel == "о":
                current += "o"
                syllables.append(current); current = ""
                continue
        if letter == "י" and vowel is None and "ִ" in prev_marks:
            continue

        if letter in IPA_HARD and has_dagesh:
            snd = IPA_HARD[letter]
        elif letter == "ש":
            snd = "s" if SIN_DOT in marks else "ʃ"
        else:
            snd = IPA_CONSONANTS[letter]

        is_last = nxt is None or nxt[0] == " "
        if is_last and letter in ("ה", "א") and vowel is None:
            continue

        # патах гнува: гласная звучит ПЕРЕД буквой
        if is_last and letter in ("ע", "ח") and "ַ" in marks:
            syllables.append(current + "a") if current else syllables.append("a")
            current = snd
            continue

        current += snd
        if vowel:
            current += IPA_VOWELS.get(vowel, vowel)
            syllables.append(current); current = ""
        elif SHVA in marks:
            at_start = i == 0 or units[i - 1][0] == " "
            # Два шва подряд: второй всегда читается. Иначе תִּכְתְּבִי
            # выходило «тихтви» вместо «тихтеви».
            after_shva = (not at_start
                          and SHVA in units[i - 1][1]
                          and not prev_was_vocal_shva)
            if at_start or after_shva:
                current += "e"
                syllables.append(current); current = ""
                prev_was_vocal_shva = True
                continue
            # шва-нах: согласный ЗАКРЫВАЕТ предыдущий слог, а не
            # начинает следующий. Без этого выходило hi.tka.ʃaˈʁti
            # вместо hit.ka.ʃarˈti, и синтезатор относил ударение
            # не к тому слогу.
            if syllables and not any(v in current for v in "aeiou"):
                syllables[-1] += current
                current = ""
            prev_was_vocal_shva = False
        else:
            prev_was_vocal_shva = False

    if current:                      # хвост из согласных — в последний слог
        if syllables:
            syllables[-1] += current
        else:
            syllables.append(current)

    if not syllables:
        return ""

    # Порядок важен: сначала явные исключения, затем глагольные
    # окончания (они надёжнее, потому что задают ударение грамматически),
    # и только потом правило по виду слова.
    exception = _stress_exception(word)
    by_ending = _verb_ending_stress(units)
    if exception == "milel":
        penultimate = True
    elif exception == "milra":
        penultimate = False
    elif by_ending is not None:
        penultimate = by_ending
    else:
        penultimate = _is_segolate(units) or _helping_hiriq(units)
    stressed = len(syllables) - (2 if penultimate and len(syllables) > 1 else 1)

    # Формат проверен на слух (tools/stress_variants.py): точка стоит
    # между ВСЕМИ слогами, а знак ударения добавляется к ней, а не
    # заменяет её — ta.ˈpu.aχ. Если ставить ˈ вместо точки (taˈpu.aχ),
    # синтезатор относит ударение не к тому слогу.
    out = []
    for n, syl in enumerate(syllables):
        if n > 0:
            out.append(".")
        if n == stressed:
            out.append("ˈ")
        out.append(syl)
    return "".join(out)


def to_ktiv_male(word):
    """Огласованная запись -> обычное израильское письмо (כתיב מלא).

    Нужно для синтеза речи: модели TTS обучены на живом тексте без
    огласовок, и диакритика их сбивает. Отличается от нормализации в
    matching.py тем, что здесь важно получить ПРАВИЛЬНЫЙ иврит:
    конечные формы букв сохраняются (שלום, а не שלומ), иначе синтезатор
    читает бессмыслицу.

    Правила, которые реально нужны нашему банку:
      кубуц ֻ           -> ו      (סֻכָּר -> סוכר)
      холам ֹ           -> ו      (חֹם -> חום), но не перед א: רֹאשׁ -> ראש
      окончание ַיִם     -> ַיִים   (מִכְנָסַיִם -> מכנסיים)
    """
    units = _split(word)
    out = []
    for i, (letter, marks) in enumerate(units):
        out.append(letter)
        if letter == " ":
            continue
        nxt = units[i + 1][0] if i + 1 < len(units) else None

        if "ֻ" in marks:                      # кубуц
            out.append("ו")
        elif "ֹ" in marks and letter != "ו":   # холам
            # перед א вав не пишут: רֹאשׁ -> ראש
            if nxt != "א":
                out.append("ו")
        elif "ִ" in marks and letter == "י" and i >= 1 and "ַ" in units[i - 1][1]:
            # Окончание -айим удваивает йод, но только если перед ним есть
            # полноценный слог: מכנסיים, שמיים — и при этом מים, בית, עין
            # с одним йодом (там до йода всего одна буква).
            letters_before = sum(1 for l, _ in units[:i] if l != " ")
            if letters_before >= 2:
                out.append("י")

    return "".join(out)


def translit(word):
    """Произношение слова кириллицей."""
    # Слова разбираем по отдельности: камац катан определяется в пределах
    # слова, а не всей фразы.
    if " " in (word or ""):
        return " ".join(translit(w) for w in word.split())

    units = _split(word)
    whole_word_katan = unicodedata.normalize("NFC", word or "") in KAMATS_KATAN_WORDS
    res = []
    prev_was_vocal_shva = False

    for i, (letter, marks) in enumerate(units):
        if letter == " ":
            res.append(" ")
            continue
        if letter not in CONSONANTS:
            continue

        vowel = next((VOWELS[m] for m in marks if m in VOWELS), None)

        # Камац катан читается как «о»: перед хатаф-камацем (צָהֳרַיִם)
        # или в слове из списка (כָּל).
        if KAMATS in marks:
            next_marks = units[i + 1][1] if i + 1 < len(units) else []
            if whole_word_katan or HATAF_KAMATS in next_marks:
                vowel = "о"

        has_dagesh = DAGESH in marks
        prev_letter, prev_marks = units[i - 1] if i > 0 else (None, [])
        nxt = units[i + 1] if i + 1 < len(units) else None

        # ו и י часто не согласные, а часть гласной
        if letter == "ו":
            if has_dagesh and vowel is None:
                res.append("у")            # шурук וּ
                continue
            if vowel == "о":
                res.append("о")            # холам мале וֹ
                continue
        if letter == "י" and vowel is None and "ִ" in prev_marks:
            continue                        # хирик мале ִי — «и» уже выдана

        # согласный
        if letter in HARD and has_dagesh:
            snd = HARD[letter]
        elif letter == "ש":
            snd = "с" if SIN_DOT in marks else "ш"
        else:
            snd = CONSONANTS[letter]

        # немые в конце слова
        is_last = nxt is None or nxt[0] == " "
        if is_last and letter in ("ה", "א") and vowel is None:
            continue

        # «Патах гнува»: под конечными ע и ח патах читается ПЕРЕД буквой —
        # תַּפּוּחַ это «тапуах», а не «тапуха».
        if is_last and letter in ("ע", "ח") and "ַ" in marks:
            res.append("а")
            res.append(snd)
            continue

        res.append(snd)

        if vowel:
            res.append(vowel)
            prev_was_vocal_shva = False
        elif SHVA in marks:
            # Шва читается как «е» в начале слова, а внутри — если перед
            # ним стоит ещё один шва (תִּכְתְּבִי — «тихтеви», не «тихтви»).
            # В остальных случаях беззвучен.
            at_start = i == 0 or units[i - 1][0] == " "
            after_shva = (not at_start
                          and SHVA in units[i - 1][1]
                          and not prev_was_vocal_shva)
            if at_start or after_shva:
                res.append("е")
                prev_was_vocal_shva = True
            else:
                prev_was_vocal_shva = False
        else:
            prev_was_vocal_shva = False

    return "".join(res).strip()


# --- латиница: чтение для англоязычных ---
#
# Отдельного разбора не нужно: to_ipa уже прошёл по огласовкам и выдал
# транскрипцию. Латиница получается из неё подстановкой — тот же разбор,
# та же логика камац катана и беглого шва, и расходиться им не с чего.
#
# Набор символов на выходе to_ipa закрытый (проверено по всему словарю):
# .abdefhijklmnopstuvzɡʁʃˈχ — поэтому таблица ниже полная, а не «на что
# хватило». Незнакомый символ означает, что to_ipa научился новому звуку,
# и его нужно назвать здесь же.
IPA_TO_LATIN = {
    "χ": "kh",   # ח и כ. Не «ch»: по-английски «ch» читается как «ч»,
                 # и «lechem» превращается в «лечем».
    "ʁ": "r",    # увулярное «р» израильтян; латиницей всё равно «r»
    "ʃ": "sh",
    "ɡ": "g",    # это не латинская g, а знак IPA U+0261
    "j": "y",    # «байит» -> bayit, а не bajit
}

# Служебные знаки транскрипции: точка делит слоги, вертикальный штрих
# помечает ударение. В кириллическом варианте их нет — не показываем и
# здесь, иначе два языка выглядели бы по-разному без причины.
#
# Ударение при этом теряется, хотя to_ipa его знает: «бокер» и «бокЕр»
# для новичка разные слова. Показывать его стоит, но тогда сразу в обоих
# языках, а это отдельное решение по оформлению карточки.
IPA_MARKS = ".ˈ"


def to_latin(word):
    """Произношение слова латиницей: לֶחֶם -> lehem."""
    out = []
    for ch in to_ipa(word):
        if ch in IPA_MARKS:
            continue
        out.append(IPA_TO_LATIN.get(ch, ch))
    return "".join(out)


def reading(word, lang="ru"):
    """Чтение слова на языке интерфейса."""
    return to_latin(word) if lang == "en" else translit(word)
