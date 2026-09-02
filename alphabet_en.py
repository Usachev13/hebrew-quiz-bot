# -*- coding: utf-8 -*-
"""
Английские названия букв, звуков и слогов.

Курс алфавита — единственное место, где переводится и ответ тоже.
В словаре ответ всегда на иврите: спросили «хлеб» или «bread», ответ
один — לֶחֶם. А здесь ответ это название буквы, и по-английски она
называется иначе: не «хет», а «chet».

О записи звуков
---------------
Звук описывается средствами языка интерфейса, а не единой системой.
`ח` по-русски «х горловое», по-английски «guttural kh»: у англоязычного
человека нет буквы «х», и запись «kh» ему говорит больше, чем любой
значок IPA, которого он на первом уроке не читает.

По той же причине названия букв даны в общепринятой английской
транслитерации из учебников (chet, tsadi, kuf), а не в академической
(ḥet, ṣade, qof). Человек встретит их в ульпане именно в таком виде.

Слоги
-----
`шэ` записано как «she», а не «sheh». Гласная в английском чтении
«she» звучит иначе, но карточка спрашивает не произношение слога, а
какой знак огласовки перед ним стоит: варианты ответа отличаются
гласной буквой (sha / shi / shu / she / sho), и этого достаточно.
Добавлять «h» значило бы вводить свою систему записи ради случая,
которого в карточке нет.
"""

# Шаблоны вопросов. Вынесены сюда, а не в общий словарь интерфейса,
# потому что подставляется в них ивритский знак — вопрос собирается
# рядом с данными, которые в него попадают.
P_LETTER = "the letter {}"
P_SOUND = "the sound of {}"
P_LOOKS = "what does «{}» look like"
P_FINAL = "the final form of {}"
P_NIQQUD = "the vowel sign {} — which sound"
P_READ = "read {}"


LETTER_NAMES_EN = {
    "א": "alef",
    "ב": "bet / vet",
    "ג": "gimel",
    "ד": "dalet",
    "ה": "hey",
    "ו": "vav",
    "ז": "zayin",
    "ח": "chet",
    "ט": "tet",
    "י": "yud",
    "כ": "kaf / chaf",
    "ל": "lamed",
    "מ": "mem",
    "נ": "nun",
    "ס": "samech",
    "ע": "ayin",
    "פ": "pey / fey",
    "צ": "tsadi",
    "ק": "kuf",
    "ר": "resh",
    "ש": "shin / sin",
    "ת": "tav",
}

LETTER_SOUNDS_EN = {
    "א": "no sound",
    "ב": "b / v",
    "ג": "g",
    "ד": "d",
    "ה": "h, silent at the end",
    "ו": "v / o / u",
    "ז": "z",
    "ח": "guttural kh",
    "ט": "t",
    "י": "y / i",
    "כ": "k / kh",
    "ל": "l",
    "מ": "m",
    "נ": "n",
    "ס": "s",
    "ע": "no sound, guttural",
    "פ": "p / f",
    "צ": "ts",
    "ק": "k",
    "ר": "r",
    "ש": "sh / s",
    "ת": "t",
}

# Точка внутри буквы (дагеш) или сбоку меняет звук. Ключ — буква вместе
# со знаком: «בּ» и «ב» это разные строки, и словарь их различает.
DOTTED_EN = {
    "בּ": "b",
    "ב": "v",
    "כּ": "k",
    "כ": "kh",
    "פּ": "p",
    "פ": "f",
    "שׁ": "sh",
    "שׂ": "s",
}

NIQQUD_EN = {
    "בַ": "a",
    "בָ": "a",
    "בֶ": "e",
    "בֵ": "e",
    "בִ": "i",
    "בֹ": "o",
    "בֻ": "u",
    "בוּ": "u",
    "בְ": "no vowel",
}

SYLLABLES_EN = {
    "מָ": "ma", "מִ": "mi", "מוּ": "mu", "מֶ": "me", "מֹ": "mo",
    "שָׁ": "sha", "שִׁ": "shi", "שׁוּ": "shu", "שֶׁ": "she", "שֹׁ": "sho",
    "לָ": "la", "לִ": "li", "לוּ": "lu", "לֵ": "le", "לֹ": "lo",
    "תָ": "ta", "תִ": "ti", "תוּ": "tu", "תֶ": "te", "תֹ": "to",
    "רָ": "ra", "רִ": "ri", "רוּ": "ru", "רֵ": "re", "רֹ": "ro",
    "דָ": "da", "דִ": "di", "דוּ": "du", "דֶ": "de", "דֹ": "do",
    "קָ": "ka", "קִ": "ki", "קוּ": "ku", "קֵ": "ke", "קֹ": "ko",
    "נָ": "na", "נִ": "ni", "נוּ": "nu", "נֶ": "ne", "נֹ": "no",
}

# Чем похожие буквы отличаются на письме. Показывается подсказкой, когда
# человек путает пару. Описание привязано к тому, что видно глазом,
# поэтому переводится дословно.
CONFUSABLE_EN = {
    "ב": "bet: has a «heel» at the bottom right",
    "כ": "kaf: rounded, no «heel»",
    "ד": "dalet: sharp corner top right, short leg",
    "ר": "resh: rounded corner, no overhang",
    "ה": "hey: separate left leg, gap at the top",
    "ח": "chet: solid crossbar, no gap",
    "ו": "vav: a single vertical stroke",
    "ז": "zayin: a stroke with a cap on top",
    "ן": "nun sofit: long stroke, drops below the line",
    "ם": "mem sofit: a fully closed square",
    "ס": "samech: rounded and fully closed",
    "ג": "gimel: two legs, the left one shorter",
    "נ": "nun: narrow, with a leg to the right",
    "ע": "ayin: two legs meeting in a stem",
    "צ": "tsadi: two legs, the right joins from above",
    "ט": "tet: rounded, with a curl inside",
    "מ": "mem: almost closed, gap at the bottom left",
}
