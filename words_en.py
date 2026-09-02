# -*- coding: utf-8 -*-
"""
Английские подсказки к словарю и глаголам.

Почему отдельным файлом, а не третьим элементом кортежа в words.py
--------------------------------------------------------------------
Словарь пополняется руками и читается глазами: строка
`("хлеб", "לֶחֶם")` понятна с первого взгляда, а
`("хлеб", "לֶחֶם", "bread")` уже нет — при десяти языках она станет
нечитаемой. Перевод живёт рядом, но отдельно, и подключается по ключу.

Ключ — `cid` карточки (см. cards.py), а не русское слово и не иврит.
Русское сломается от правки опечатки, иврит — от правки огласовки;
`cid` переживает и то и другое, потому что собран из категории и
согласного скелета.

Полнота проверяется на импорте quiz.py: если слово добавили, а перевод
забыли, тест `tools/check_i18n.py` это назовёт поимённо. Молча показать
англоязычному человеку русскую подсказку — худший исход, чем упасть.

Что учтено при переводе
-----------------------
Переводится не русское слово, а карточка целиком: смысл задаёт иврит.
Поэтому `שֻׁלְחָן` — «table», хотя по-русски «стол», а `רִצְפָּה` —
«floor» в значении поверхности, и это единственное её значение.

Пояснения в скобках оставлены там же, где они есть по-русски, но
переписаны под английскую грамматику: русскому «ты (муж.)» в английском
соответствует «you (m.)», потому что само слово «you» рода не имеет и
без пометки карточка стала бы неразличимой.

Израильские реалии не переводятся дословно: `קֻפַּת חוֹלִים` — не
«sick fund», а «health fund (kupat holim)»: человек встретит это слово
на вывеске и должен узнать его, а не понять этимологию.
"""

# ---------------------------------------------------------------- слова

WORDS = {
    # прилагательные
    "adjectives:טוב": "good",
    "adjectives:רע": "bad",
    "adjectives:יפה": "beautiful",
    "adjectives:חדש": "new",
    "adjectives:ישן": "old (not new)",
    "adjectives:גדול": "big",
    "adjectives:קטן": "small",
    "adjectives:עתיק": "ancient",
    "adjectives:מיוחד": "special",
    "adjectives:מענין": "interesting",

    # наречия
    "adverbs:הרבה": "a lot",
    "adverbs:בשקט": "quietly",
    "adverbs:מהר": "fast",
    "adverbs:לאט": "slowly",
    "adverbs:קשה": "hard (difficult)",

    # вопросительные слова
    "question_words:מה": "what",
    "question_words:מי": "who",
    "question_words:איפה": "where",
    "question_words:לאן": "where to",
    "question_words:מאין": "where from",
    "question_words:איזה": "which (m.)",
    "question_words:איזו": "which (f.)",
    "question_words:אילו": "which (pl.)",
    "question_words:מתי": "when",
    "question_words:למה": "why",

    # частицы
    "particles:יש": "there is / there are",
    "particles:אין": "there is no",
    "particles:כל": "all / every",
    "particles:אבל": "but",
    "particles:משהו": "something",
    "particles:מישהו": "someone",

    # количественные числительные (мужской род)
    "cardinals:אחד": "one",
    "cardinals:שנים": "two",
    "cardinals:שלושה": "three",
    "cardinals:ארבעה": "four",
    "cardinals:חמשה": "five",
    "cardinals:עשרה": "ten",
    "cardinals:עשרים": "twenty",
    "cardinals:מאה": "a hundred",
    "cardinals:אלף": "a thousand",

    # порядковые
    "ordinals:ראשון": "first",
    "ordinals:שני": "second",
    "ordinals:שלישי": "third",
    "ordinals:חמישי": "fifth",
    "ordinals:עשירי": "tenth",

    # местоимения-дополнения
    "object_pronouns:אותי": "me (object)",
    "object_pronouns:אותו": "him (object)",
    "object_pronouns:אותה": "her (object)",
    "object_pronouns:אותנו": "us (object)",
    "object_pronouns:אתכם": "you (object, pl.)",
    "object_pronouns:אותם": "them (object)",

    # личные местоимения
    "personal_pronouns:אני": "I",
    "personal_pronouns:אתה": "you (m.)",
    "personal_pronouns:את": "you (f.)",
    "personal_pronouns:הוא": "he",
    "personal_pronouns:היא": "she",
    "personal_pronouns:אנחנו": "we",
    "personal_pronouns:אתם": "you (m. pl.)",
    "personal_pronouns:אתן": "you (f. pl.)",
    "personal_pronouns:הם": "they (m.)",
    "personal_pronouns:הן": "they (f.)",

    # приветствия
    "greetings:שלום": "hello / peace",
    "greetings:בקר טוב": "good morning",
    "greetings:ערב טוב": "good evening",
    "greetings:לילה טוב": "good night",
    "greetings:תודה": "thank you",
    "greetings:בבקשה": "please / you're welcome",
    "greetings:סליחה": "sorry / excuse me",
    "greetings:להתראות": "goodbye",
    "greetings:נעים מאד": "nice to meet you",
    "greetings:כן": "yes",
    "greetings:לא": "no / not",
    "greetings:אולי": "maybe",

    # семья
    "family:אמא": "mum",
    "family:אבא": "dad",
    "family:בן": "son",
    "family:בת": "daughter",
    "family:אח": "brother",
    "family:אחות": "sister",
    "family:בעל": "husband",
    "family:אשה": "woman / wife",
    "family:גבר": "man",
    "family:ילד": "child",
    "family:ילדה": "girl",
    "family:סבא": "grandfather",
    "family:סבתא": "grandmother",
    "family:הורים": "parents",
    "family:משפחה": "family",
    "family:חבר": "friend (m.)",
    "family:חברה": "friend (f.)",
    "family:שם": "name",

    # еда
    "food:לחם": "bread",
    "food:מים": "water",
    "food:חלב": "milk",
    "food:גבינה": "cheese",
    "food:ביצה": "egg",
    "food:בשר": "meat",
    "food:עוף": "chicken (meat)",
    "food:דג": "fish",
    "food:אורז": "rice",
    "food:מרק": "soup",
    "food:סלט": "salad",
    "food:ירקות": "vegetables",
    "food:פרות": "fruit",
    "food:תפוח": "apple",
    "food:תפוז": "orange",
    "food:עגבניה": "tomato",
    "food:מלפפון": "cucumber",
    "food:חמאה": "butter",
    "food:סכר": "sugar",
    "food:מלח": "salt",
    "food:קפה": "coffee",
    "food:תה": "tea",
    "food:יין": "wine",
    "food:ארוחת בקר": "breakfast",
    "food:ארוחת צהרים": "lunch",
    "food:ארוחת ערב": "dinner",

    # дом
    "home:בית": "house",
    "home:דירה": "flat",
    "home:חדר": "room",
    "home:מטבח": "kitchen",
    "home:שרותים": "toilet",
    "home:סלון": "living room",
    "home:חדר שנה": "bedroom",
    "home:שלחן": "table",
    "home:כסא": "chair",
    "home:מטה": "bed",
    "home:דלת": "door",
    "home:חלון": "window",
    "home:ארון": "wardrobe",
    "home:מקרר": "fridge",
    "home:מפתח": "key",
    "home:רצפה": "floor",
    "home:מרפסת": "balcony",
    "home:מדרגות": "stairs",

    # город
    "city:עיר": "city",
    "city:רחוב": "street",
    "city:ככר": "square",
    "city:חנות": "shop",
    "city:שוק": "market",
    "city:בנק": "bank",
    "city:דאר": "post",
    "city:בית מרקחת": "pharmacy",
    "city:בית חולים": "hospital",
    "city:בית ספר": "school",
    "city:אוניברסיטה": "university",
    "city:מסעדה": "restaurant",
    "city:בית קפה": "café",
    "city:פארק": "park",
    "city:חוף": "beach",
    "city:בית כנסת": "synagogue",
    "city:מלון": "hotel",
    "city:סופרמרקט": "supermarket",

    # транспорт
    "transport:מכונית": "car",
    "transport:אוטובוס": "bus",
    "transport:רכבת": "train",
    "transport:מטוס": "plane",
    "transport:מונית": "taxi",
    "transport:אופנים": "bicycle",
    "transport:תחנה": "stop / station",
    "transport:כרטיס": "ticket",
    "transport:דרך": "road / way",
    "transport:רמזור": "traffic light",
    "transport:פקק": "traffic jam",
    "transport:נמל תעופה": "airport",

    # время
    "time:יום": "day",
    "time:לילה": "night",
    "time:בקר": "morning",
    "time:ערב": "evening",
    "time:צהרים": "noon",
    "time:שבוע": "week",
    "time:חדש": "month",
    "time:שנה": "year",
    "time:שעה": "hour",
    "time:דקה": "minute",
    "time:היום": "today",
    "time:אתמול": "yesterday",
    "time:מחר": "tomorrow",
    "time:עכשיו": "now",
    "time:אחר כך": "afterwards",
    "time:תמיד": "always",
    "time:אף פעם": "never",
    "time:לפעמים": "sometimes",
    "time:יום ראשון": "Sunday",
    "time:יום שני": "Monday",
    "time:שבת": "Saturday / Shabbat",

    # погода
    "weather:מזג אויר": "weather",
    "weather:שמש": "sun",
    "weather:גשם": "rain",
    "weather:רוח": "wind",
    "weather:ענן": "cloud",
    "weather:חם": "heat",
    "weather:קר": "cold (noun)",
    "weather:שלג": "snow",
    "weather:שמים": "sky",
    "weather:ים": "sea",

    # здоровье
    "health:רופא": "doctor",
    "health:חולה": "ill",
    "health:בריא": "healthy",
    "health:כאב": "pain",
    "health:ראש": "head",
    "health:יד": "hand / arm",
    "health:רגל": "leg / foot",
    "health:עין": "eye",
    "health:אזן": "ear",
    "health:פה": "mouth",
    "health:אף": "nose",
    "health:שן": "tooth",
    "health:בטן": "belly",
    "health:גב": "back",
    "health:לב": "heart",
    "health:תרופה": "medicine",
    "health:קפת חולים": "health fund (kupat holim)",

    # покупки
    "shopping:כסף": "money",
    "shopping:מחיר": "price",
    "shopping:יקר": "expensive",
    "shopping:זול": "cheap",
    "shopping:הנחה": "discount",
    "shopping:חשבון": "bill",
    "shopping:קפה": "cash desk",
    "shopping:כרטיס אשראי": "credit card",
    "shopping:עדף": "change (money back)",
    "shopping:שקל": "shekel",
    "shopping:מוכר": "shop assistant",
    "shopping:לקוח": "customer",
    "shopping:תיק": "bag",
    "shopping:שקית": "plastic bag",

    # работа и учёба
    "work_study:עבודה": "work",
    "work_study:משרד": "office",
    "work_study:מנהל": "manager",
    "work_study:משכרת": "salary",
    "work_study:שעור": "lesson",
    "work_study:מורה": "teacher",
    "work_study:תלמיד": "pupil",
    "work_study:סטודנט": "student",
    "work_study:ספר": "book",
    "work_study:מחברת": "notebook",
    "work_study:עט": "pen",
    "work_study:שאלה": "question",
    "work_study:תשובה": "answer",
    "work_study:מבחן": "exam",

    # одежда
    "clothes:בגדים": "clothes",
    "clothes:חלצה": "shirt",
    "clothes:מכנסים": "trousers",
    "clothes:שמלה": "dress",
    "clothes:חצאית": "skirt",
    "clothes:נעלים": "shoes",
    "clothes:מעיל": "coat",
    "clothes:כובע": "hat",
    "clothes:גרבים": "socks",
    "clothes:משקפים": "glasses",

    # эмоции и состояния
    "emotions:שמחה": "joy",
    "emotions:עצב": "sadness",
    "emotions:אהבה": "love",
    "emotions:פחד": "fear",
    "emotions:מאשר": "happy",
    "emotions:כועס": "angry",
    "emotions:רעב": "hungry",
    "emotions:צמא": "thirsty",
    "emotions:עיף": "tired",
    "emotions:מרצה": "pleased",
    "emotions:רגוע": "calm",

    # предлоги места
    "place_prepositions:על": "on",
    "place_prepositions:מתחת": "under",
    "place_prepositions:מעל": "above",
    "place_prepositions:ליד": "next to",
    "place_prepositions:בין": "between",
    "place_prepositions:בתוך": "inside",
    "place_prepositions:בחוץ": "outside",
    "place_prepositions:לפני": "before / in front of",
    "place_prepositions:אחרי": "after",
    "place_prepositions:כאן": "here",
    "place_prepositions:שם": "there",
}


# -------------------------------------------------------------- глаголы
#
# Инфинитив по-английски пишем с «to»: без него «work» неотличимо от
# существительного «работа», которое в словаре уже есть.

VERBS = {
    "paal_final_hey:לקנות": "to buy",
    "paal_final_hey:לבנות": "to build",
    "paal_final_hey:לרצות": "to want",
    "paal_final_hey:לעלות": "to go up / to cost",
    "paal_final_hey:לראות": "to see",
    "paal_final_hey:לקרות": "to happen",
    "paal_final_hey:לענות": "to answer",
    "paal_final_hey:לבכות": "to cry",
    "paal_final_hey:לשתות": "to drink",
    "paal_final_hey:להיות": "to be",
    "paal_final_hey:לפנות": "to turn / to approach",
    "paal_final_hey:לעשות": "to do",

    "paal_regular:לכתוב": "to write",
    "paal_regular:לקרוא": "to read",
    "paal_regular:ללמוד": "to study",
    "paal_regular:לאכול": "to eat",
    "paal_regular:לחשוב": "to think",
    "paal_regular:לעבוד": "to work",
    "paal_regular:לבדוק": "to check",
    "paal_regular:לאהוב": "to love",
    "paal_regular:לעמוד": "to stand",
    "paal_regular:להרוג": "to kill",
    "paal_regular:לרקוד": "to dance",
    "paal_regular:לארוז": "to pack",
    "paal_regular:לשכור": "to rent",
    "paal_regular:לבחור": "to choose",
    "paal_regular:למכור": "to sell",
    "paal_regular:לכאוב": "to ache",
    "paal_regular:לדאוג": "to worry",

    "paal_ayin_het:לשלח": "to send",
    "paal_ayin_het:לנסע": "to travel",
    "paal_ayin_het:לפתח": "to open",
    "paal_ayin_het:לפגע": "to hurt",
    "paal_ayin_het:לקרע": "to tear",

    "piel:לדבר": "to speak",
    "piel:לחפש": "to look for",
    "piel:לטיל": "to walk around / to travel",
    "piel:לקבל": "to receive",
    "piel:לשלם": "to pay",
    "piel:לשחק": "to play",
    "piel:לנגן": "to play music",
    "piel:לספר": "to tell",

    "hifil:להרגיש": "to feel",
    "hifil:להזמין": "to order / to invite",
    "hifil:להסביר": "to explain",
    "hifil:להפסיק": "to stop",
    "hifil:להצליח": "to succeed",
    "hifil:להתחיל": "to begin",
    "hifil:להבין": "to understand",
    "hifil:להגיד": "to say",

    "hitpael:להתחתן": "to get married",
    "hitpael:להתקשר": "to call (phone)",
    "hitpael:להתפלל": "to pray",
    "hitpael:להתנדב": "to volunteer",
    "hitpael:להתרגל": "to get used to",
    "hitpael:להתפתח": "to develop",
    "hitpael:להתרגש": "to be moved",
    "hitpael:להתקרב": "to come closer",
    "hitpael:להתגרש": "to get divorced",
    "hitpael:להתרחץ": "to wash / to bathe",
    "hitpael:להתנהג": "to behave",
    "hitpael:להתחזק": "to grow stronger",

    "exceptions:לבוא": "to come",
    "exceptions:לרוץ": "to run",
    "exceptions:לגור": "to live (reside)",
    "exceptions:לקום": "to get up",
    "exceptions:לנוח": "to rest",
    "exceptions:לשים": "to put",
    "exceptions:לטוס": "to fly",
    "exceptions:ללכת": "to go / to walk",
    "exceptions:לרדת": "to go down",
    "exceptions:לשבת": "to sit",
    "exceptions:לדעת": "to know",
    "exceptions:לגעת": "to touch",
    "exceptions:לקחת": "to take",
}


# --------------------------------------------------- значения по корню
#
# Подсказка к форме глагола собирается как «писать (לִכְתּוֹב) — я».
# Английский вариант берёт значение отсюда: ключ — корень, потому что
# спряжения разложены по корням, а не по инфинитивам.
#
# Формы глагола называем герундием («writing»), а не инфинитивом:
# карточка спрашивает не «как будет „писать“», а «какая форма у „я“ в
# прошедшем» — «to write — I» читалось бы как приказ, «writing — I» как
# заголовок таблицы спряжения, чем оно и является.

ROOT_MEANINGS = {
    # пааль, правильные
    "כתב": "to write",        "למד": "to study",
    "אכל": "to eat",          "חשב": "to think",
    "עבד": "to work",         "בדק": "to check",
    "אהב": "to love",         "עמד": "to stand",
    "הרג": "to kill",         "רקד": "to dance",
    "ארז": "to pack",         "שכר": "to rent",
    "בחר": "to choose",       "מכר": "to sell",
    "כאב": "to ache",         "דאג": "to worry",
    "פגש": "to meet",         "שאל": "to ask",
    "עזר": "to help",         "קרא": "to read",

    # пааль, третья корневая — «хей»
    "קנה": "to buy",          "בנה": "to build",
    "רצה": "to want",         "עלה": "to go up / to cost",
    "ראה": "to see",          "קרה": "to happen",
    "ענה": "to answer",       "בכה": "to cry",
    "שתה": "to drink",        "פנה": "to turn / to approach",
    "עשה": "to do",           "היה": "to be",

    # пааль, вторая или третья корневая — гортанная
    "שלח": "to send",         "נסע": "to travel",
    "פתח": "to open",         "פגע": "to hurt",
    "קרע": "to tear",

    # пиэль
    "דבר": "to speak",        "חפש": "to look for",
    "קבל": "to receive",      "שלם": "to pay",
    "שחק": "to play",         "נגן": "to play music",
    "ספר": "to tell",         "טיל": "to walk around / to travel",

    # хифиль
    "רגש": "to feel",         "זמן": "to order / to invite",
    "סבר": "to explain",      "פסק": "to stop",
    "צלח": "to succeed",      "תחל": "to begin",
    "בין": "to understand",

    # хитпаэль
    "חתן": "to get married",  "קשר": "to call (phone)",
    "פלל": "to pray",         "נדב": "to volunteer",
    "רגל": "to get used to",  "פתח_ה": "to develop",
    "רגש_ה": "to be moved",   "קרב": "to come closer",
    "גרש": "to get divorced", "רחץ": "to wash / to bathe",
    "נהג": "to behave",       "חזק": "to grow stronger",

    # неправильные
    "בוא": "to come",         "רוץ": "to run",
    "גור": "to live (reside)", "קום": "to get up",
    "נוח": "to rest",         "שים": "to put",
    "טוס": "to fly",          "הלך": "to go / to walk",
    "ירד": "to go down",      "ישב": "to sit",
    "ידע": "to know",         "נגע": "to touch",
    "לקח": "to take",
}


# ------------------------------------------------------- лица и формы
#
# Подписи к формам глагола. В английском «you» не различает ни рода, ни
# числа, поэтому без пометок половина карточек стала бы неотличима друг
# от друга: «you» в четырёх строках таблицы.

PAST_LABELS = {
    "אני": "I", "אתה": "you (m.)", "את": "you (f.)",
    "הוא": "he", "היא": "she", "אנחנו": "we",
    "אתם": "you (m. pl.)", "אתן": "you (f. pl.)", "הם/הן": "they",
}

PRESENT_LABELS = {
    "m_sg": "masculine singular", "f_sg": "feminine singular",
    "m_pl": "masculine plural",   "f_pl": "feminine plural",
}

FUTURE_LABELS = {
    "אני": "I", "אתה/היא": "you (m.) / she", "את": "you (f.)",
    "הוא": "he", "אנחנו": "we", "אתם/אתן": "you (pl.)", "הם/הן": "they",
}
