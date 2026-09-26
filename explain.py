# -*- coding: utf-8 -*-
"""
Разбор карточки: почему ответ такой.

Зачем
-----
До сих пор приложение только спрашивало. Человек мог прогнать карточку
сто раз и не узнать, почему «כּוֹתֵב» одинаково у «я», «ты» и «он», —
он просто заучивал, что вот эта кнопка верная. Это работает для слов и
почти не работает для форм: форм 1536, и выучить их списком нельзя, а
по правилу — можно, потому что правил семь.

Знание для этого уже лежало в проекте, просто не показывалось:
* биньян и корень известны у всех 77 глаголов;
* семнадцать описаний того, чем похожие буквы отличаются на письме,
  были написаны, переведены на английский и не показаны никому;
* ударение вычисляется разбором огласовок.

Здесь всё это превращается в текст для человека.

Чего здесь нет
--------------
Статей по грамматике. Смихут, предлоги, полная таблица биньянов — это
отдельный раздел и отдельная работа, для которой нужны материалы
преподавателя. Здесь только то, что выводится из наших данных.

И главное правило: если сказать нечего — молчим. Пустая подсказка
«это слово надо запомнить» хуже отсутствия подсказки: она занимает
место и приучает не читать.
"""

import re

from alphabet import CONFUSABLE, DOTTED, LETTERS
import grammar
import hebrew_meta
from conjugations import CONJUGATIONS, PAST_LABELS, PRESENT_LABELS, FUTURE_LABELS
from translit import to_ipa

_CONF = dict(CONFUSABLE)

# Корень записывают обычными буквами, даже если в слове они конечные:
# корень «идти» — ה־ל־כ, а не ה־ל־ך. Ключи в CONJUGATIONS хранят его
# так, как он выглядит в инфинитиве, поэтому при показе разворачиваем.
_FROM_FINAL = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}
_FINAL_OF = {base: final for base, _n, _s, final in LETTERS if final}

# Биньян — модель, по которой строится глагол. Название нужно и
# по-английски: человек встретит его в любом учебнике.
BINYAN_EN = {
    "пааль": "pa'al",
    "пааль (ל״ה)": "pa'al (final hey)",
    "пааль (гортанная)": "pa'al (guttural)",
    "пиэль": "pi'el",
    "ифиль": "hif'il",
    "итпаэль": "hitpa'el",
    "исключения / полые": "irregular / hollow",
}

T = {
    "binyan": {"ru": "Биньян {b}, корень {r}.",
               "en": "Binyan {b}, root {r}."},
    # «исключения / полые» — не название биньяна, а пометка о том, что
    # глагол строится не по общему правилу. Называть это биньяном
    # значит сбивать: человек пойдёт искать такой биньян и не найдёт.
    "irregular": {"ru": "Неправильный глагол, корень {r}. "
                        "Его формы не выводятся из общего правила — "
                        "их запоминают.",
                  "en": "An irregular verb, root {r}. Its forms don't "
                        "follow the general rule — they're memorised."},
    "present": {
        "ru": "Настоящее время не различает лицо — только род и число. "
              "«я», «ты» и «он» говорят одинаково.",
        "en": "The present tense doesn't mark person — only gender and "
              "number. «I», «you» and «he» all say the same thing.",
    },
    "present_forms": {"ru": "Все четыре формы: {f}", "en": "All four forms: {f}"},
    "past": {
        "ru": "В прошедшем лицо задаёт окончание, поэтому местоимение "
              "можно опустить: «{f}» понятно и без него.",
        "en": "In the past tense the ending marks the person, so the "
              "pronoun can be dropped: «{f}» is clear without it.",
    },
    "future": {
        "ru": "В будущем лицо задаёт приставка: א — «я», ת — «ты» и «она», "
              "י — «он», נ — «мы».",
        "en": "In the future the prefix marks the person: א for «I», "
              "ת for «you» and «she», י for «he», נ for «we».",
    },
    "confuse": {"ru": "Эти две буквы легко спутать:",
                "en": "These two letters are easy to confuse:"},
    "dagesh": {
        "ru": "Точка внутри буквы (дагеш) делает звук твёрдым: "
              "בּ «б» против ב «в», כּ «к» против כ «х», פּ «п» против פ «ф».",
        "en": "A dot inside the letter (dagesh) hardens the sound: "
              "בּ «b» vs ב «v», כּ «k» vs כ «kh», פּ «p» vs פ «f».",
    },
    "final": {
        "ru": "В конце слова пять букв пишутся иначе: {pairs}. "
              "Звук при этом не меняется.",
        "en": "Five letters are written differently at the end of a word: "
              "{pairs}. The sound stays the same.",
    },
    # Категорию слова не называем. Ударение на первом слоге бывает у
    # сеголатных (לֶחֶם), но и у двойственных форм вроде מַיִם — а
    # различить их по написанию мы не умеем. Утверждать «это
    # сеголатное» означало бы уверенно сказать неправду в части
    # случаев. Говорим факт, который верен всегда.
    "smichut": {
        "ru": "Это смихут — два существительных подряд. Первое меняет "
              "форму: «{base}» ({gloss}) превращается в «{head}». "
              "Артикль ставится ко второму слову, а не к первому.",
        "en": "This is smichut — two nouns in a row. The first one "
              "changes shape: «{base}» ({gloss}) becomes «{head}». "
              "The article goes with the second word, not the first.",
    },
    "prep": {
        "ru": "Это предлог «{base}» с местоименным окончанием. "
              "В иврите предлоги склоняются, как глаголы по лицам.",
        "en": "This is the preposition «{base}» with a pronoun ending. "
              "In Hebrew prepositions decline, much like verbs do.",
    },
    "stress": {
        "ru": "Ударение здесь на первом слоге. В иврите оно обычно на "
              "последнем, поэтому такие слова легко прочитать неверно — "
              "их стоит запомнить отдельно.",
        "en": "The stress here falls on the first syllable. In Hebrew it "
              "usually falls on the last, so words like this are easy to "
              "misread — worth remembering separately.",
    },
    "marker_past": {
        "ru": "«אֶתְמוֹל» (вчера) требует прошедшего времени.",
        "en": "«אֶתְמוֹל» (yesterday) calls for the past tense.",
    },
    "marker_present": {
        "ru": "«עַכְשָׁיו» (сейчас) требует настоящего времени.",
        "en": "«עַכְשָׁיו» (now) calls for the present tense.",
    },
    "marker_future": {
        "ru": "«מָחָר» (завтра) требует будущего времени.",
        "en": "«מָחָר» (tomorrow) calls for the future tense.",
    },
}


def _t(key, lang, **kw):
    s = T[key].get(lang, T[key]["ru"])
    return s.format(**kw) if kw else s


def _root_of(cat):
    """Корень из категории карточки: «כתב_past» -> «כתב»."""
    if not cat or "_" not in cat:
        return None
    root = cat.rsplit("_", 1)[0]
    return root if root in CONJUGATIONS else None


def _tense_of(mode, cat):
    for t in ("past", "present", "future"):
        if mode == t or (cat or "").endswith("_" + t):
            return t
    return None


def _verb(card, mode, lang):
    root = _root_of(card.cat)
    if not root:
        return []
    data = CONJUGATIONS[root]
    binyan = data["binyan"]
    if lang == "en":
        binyan = BINYAN_EN.get(binyan, binyan)
    letters = "–".join(_FROM_FINAL.get(ch, ch) for ch in root.replace("_ה", ""))
    if data["binyan"].startswith("исключения"):
        lines = [_t("irregular", lang, r=letters)]
    else:
        lines = [_t("binyan", lang, b=binyan, r=letters)]

    tense = _tense_of(mode, card.cat)
    if tense == "present":
        lines.append(_t("present", lang))
        forms = " · ".join(data["present"][s] for s in ("m_sg", "f_sg", "m_pl", "f_pl")
                           if data["present"].get(s))
        lines.append(_t("present_forms", lang, f=forms))
    elif tense == "past":
        lines.append(_t("past", lang, f=card.he))
    elif tense == "future":
        lines.append(_t("future", lang))
    return lines


def _alphabet(card, mode, given, lang):
    """Разбор для курса алфавита.

    `given` — что человек выбрал. Только зная это, можно сказать самое
    полезное: чем именно перепутанные буквы отличаются на письме.
    """
    lines = []
    letter = card.cid                    # у алфавита ключ — сама буква

    if mode == "alef_dotted":
        lines.append(_t("dagesh", lang))
    elif mode == "alef_finals":
        pairs = ", ".join(f"{b}→{f}" for b, f in list(_FINAL_OF.items()))
        lines.append(_t("final", lang, pairs=pairs))

    # Спутанные буквы: описания лежали в данных с самого начала и не
    # показывались нигде — а это ровно тот случай, когда они нужны.
    if given and given != card.answer(lang):
        wrong = _letter_by_answer(mode, given, lang)
        if wrong and wrong in _CONF and letter in _CONF:
            lines.append(_t("confuse", lang))
            lines.append(f"  {_CONF[letter]}")
            lines.append(f"  {_CONF[wrong]}")
    return lines


def _letter_by_answer(mode, given, lang):
    """По выбранному ответу находит букву, о которой он говорит."""
    import quiz
    for c in quiz.POOLS.get(mode, []):
        if c.answer(lang) == given:
            return c.cid
    return None


def _vocab(card, lang):
    """Разбор словарного слова: смихут, предлог или ударение."""
    sm = hebrew_meta.smichut_of(card.he, lang)
    if sm:
        base, gloss = sm
        return [_t("smichut", lang, base=base, gloss=gloss,
                   head=card.he.split()[0])]
    prep = hebrew_meta.preposition_of(card.he)
    if prep:
        return [_t("prep", lang, base=hebrew_meta.PREPOSITIONS[prep]["base"])]
    return _stress(card, lang)


def _stress(card, lang):
    """Слово с ударением не на последнем слоге стоит отметить."""
    he = card.he
    if not he or " " in he:
        return []
    ipa = to_ipa(he)
    syllables = ipa.split(".")
    if len(syllables) < 2:
        return []
    if syllables[0].startswith("ˈ"):
        return [_t("stress", lang)]
    return []


def page_for(card, mode):
    """Страница грамматики, к которой ведёт эта карточка. None — нет.

    Ссылка нужна там, где объяснение не помещается в три строки:
    устройство биньяна — это страница, а «настоящее не различает лицо» —
    строка, и отдельной страницы ей не надо.
    """
    if not card:
        return None
    root = _root_of(card.cat)
    if root:
        return grammar.page_for_binyan(CONJUGATIONS[root]["binyan"])
    if hebrew_meta.smichut_of(card.he):
        return "smichut"
    prep = hebrew_meta.preposition_of(card.he)
    if prep:
        return "prep." + prep
    return None


def explain(card, mode, given=None, lang="ru"):
    """Разбор карточки. None — сказать нечего, и это нормально.

    `given` — выбранный человеком ответ, если он ошибся. По нему можно
    объяснить не вообще, а именно его ошибку.
    """
    if card is None:
        return None
    lines = []

    if mode in ("past", "present", "future", "verbs", "gap_verb", "gap_who"):
        tense = _tense_of(mode, card.cat)
        if mode in ("gap_verb", "gap_who") and tense:
            lines.append(_t("marker_" + tense, lang))
        lines += _verb(card, mode, lang)
    elif mode.startswith("alef_"):
        lines += _alphabet(card, mode, given, lang)
    elif mode == "vocab":
        lines += _vocab(card, lang)

    return lines or None
