from __future__ import annotations

ABBREVIATIONS = (
    (r"\bLfd\.\s*Nr\.", "laufende Nummer"),
    (r"\bz\.\s*$", "zum Beispiel"),
    (r"^\s*b\.\s+", ""),
    (r"\bz\s*\.?\s*b\.?", "zum Beispiel"),
    (r"\bzB\b", "zum Beispiel"),
    (r"\betc\.", "ezetera"),
    (r"\busw\.", "und so weiter"),
    (r"\bca\.", "zirka"),
    (r"\bd\.\s*h\.", "das heißt"),
    (r"\bu\.\s*a\.", "unter anderem"),
    (r"\bggf\.", "gegebenenfalls"),
    (r"\bzzgl\.", "zuzüglich"),
    (r"\bDr\.", "Doktor"),
    (r"\bProf\.", "Professor"),
    (r"\bAbk\.", "Abkürzung"),
    (r"\bAbb\.", "Abbildung"),
    (r"\bgeb\.", "geboren"),
    (r"\bbspw\.", "beispielsweise"),
    (r"\bNr\.", "Nummer"),
    (r"\bggü\.", "gegenüber"),
    (r"\bKap\.", "Kapitel"),
    (r"\bS\.", "Seite"),
    (r"\bAbs\.", "Absatz"),
    (r"\bTsd\.", "Tausend"),
    (r"\bMio\.", "Millionen"),
    (r"\bMrd\.", "Milliarden"),
    (r"\bGmbH\b", "G-M-B-H"),
    (r"\bAG\b", "A-G"),
)

# Tuple: (pattern, singular, plural, gender)
# Wichtig: Einheiten MIT Punkt im Pattern stehen OHNE trailing \b im Lookahead -
# der Punkt wird durch \. am Ende des Patterns selbst konsumiert.
# Reihenfolge beachten: längere/spezifischere Patterns zuerst (mAh vor mA, kWh vor W usw.)
NUMBERED_UNITS = (
    (r"kWh",    "Kilowattstunde",     "Kilowattstunden",     "f"),
    (r"Wh",     "Wattstunde",         "Wattstunden",         "f"),
    (r"GHz",    "Gigahertz",          "Gigahertz",           None),
    (r"MHz",    "Megahertz",          "Megahertz",           None),
    (r"kHz",    "Kilohertz",          "Kilohertz",           None),
    (r"Hz",     "Hertz",              "Hertz",               None),
    (r"Std\.",  "Stunde",             "Stunden",             "f"),
    (r"Min\.",  "Minute",             "Minuten",             "f"),
    (r"Sek\.",  "Sekunde",            "Sekunden",            "f"),
    (r"Stck\.", "Stück",              "Stück",               "n"),
    (r"mAh",    "Milliamperestunde",  "Milliamperestunden",  "f"),
    (r"mA",     "Milliampere",        "Milliampere",         None),
    (r"kg",     "Kilogramm",          "Kilogramm",           None),
    (r"g",      "Gramm",              "Gramm",               None),
    (r"km",     "Kilometer",          "Kilometer",           None),
    (r"cm",     "Zentimeter",         "Zentimeter",          None),
    (r"mm",     "Millimeter",         "Millimeter",          None),
    (r"m3",     "Kubikmeter",         "Kubikmeter",          None),
    (r"m",      "Meter",              "Meter",               None),
    (r"ltr\.",  "Liter",              "Liter",               None),
    (r"EUR",    "Euro",               "Euro",                None),
    (r"W",      "Watt",               "Watt",                None),
    (r"V",      "Volt",               "Volt",                None),
    (r"Tsd\.",  "Tausend",            "Tausend",             None),
    (r"Mio\.",  "Millionen",          "Millionen",           None),
    (r"Mrd\.",  "Milliarden",         "Milliarden",          None),
)

GERMAN_SEPARATOR_DOT_PLACEHOLDER = "__WY_GERMAN_DOT__"
GERMAN_SEPARATOR_UNIT_DOT_PATTERNS = tuple(
    pattern for pattern, _singular, _plural, _gender in NUMBERED_UNITS if r"\." in pattern
)
GERMAN_SEPARATOR_EXTRA_DOT_PATTERNS = (
    r"\b\d{1,2}\.\d{1,2}\.(?:\d{2,4}\.)?",
    r"\b\d{1,6}\.(?=\s+\w)",
)
GERMAN_SEPARATOR_DOT_PATTERNS = tuple(
    pattern for pattern, _replacement in ABBREVIATIONS if r"\." in pattern
) + GERMAN_SEPARATOR_UNIT_DOT_PATTERNS + GERMAN_SEPARATOR_EXTRA_DOT_PATTERNS
