from __future__ import annotations

import re

from german_text_rules import ABBREVIATIONS, NUMBERED_UNITS

NUM_TO_WORD = {
    0: "null",
    1: "eins",
    2: "zwei",
    3: "drei",
    4: "vier",
    5: "fünf",
    6: "sechs",
    7: "sieben",
    8: "acht",
    9: "neun",
    10: "zehn",
    11: "elf",
    12: "zwölf",
    13: "dreizehn",
    14: "vierzehn",
    15: "fünfzehn",
    16: "sechzehn",
    17: "siebzehn",
    18: "achtzehn",
    19: "neunzehn",
    20: "zwanzig",
    30: "dreißig",
    40: "vierzig",
    50: "fünfzig",
    60: "sechzig",
    70: "siebzig",
    80: "achtzig",
    90: "neunzig",
}

ORDINAL_TO_WORD = {
    1: "erster",
    2: "zweiter",
    3: "dritter",
    4: "vierter",
    5: "fünfter",
    6: "sechster",
    7: "siebter",
    8: "achter",
    9: "neunter",
    10: "zehnter",
    11: "elfter",
    12: "zwölfter",
    13: "dreizehnter",
    14: "vierzehnter",
    15: "fünfzehnter",
    16: "sechzehnter",
    17: "siebzehnter",
    18: "achtzehnter",
    19: "neunzehnter",
    20: "zwanzigster",
    30: "dreißigster",
}

MONTHS = (
    r"(Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)"
)
CARDINAL_LABEL_DOT_PLACEHOLDER = "__GODE_CARDINAL_DOT__"

def number_to_words(number: int) -> str:
    """Return a German spoken form for common cardinal numbers."""
    if number < 0:
        return f"minus {number_to_words(abs(number))}"

    if number in NUM_TO_WORD:
        return NUM_TO_WORD[number]

    if number < 100:
        ones = number % 10
        tens = number - ones
        one_word = "ein" if ones == 1 else NUM_TO_WORD[ones]
        return f"{one_word}und{NUM_TO_WORD[tens]}"

    if number < 1000:
        hundreds = number // 100
        rest = number % 100
        prefix = "einhundert" if hundreds == 1 else f"{number_to_words(hundreds)}hundert"
        return prefix if rest == 0 else f"{prefix}{number_to_words(rest)}"

    if number < 1_000_000:
        thousands = number // 1000
        rest = number % 1000
        prefix = "eintausend" if thousands == 1 else f"{number_to_words(thousands)}tausend"
        return prefix if rest == 0 else f"{prefix}{number_to_words(rest)}"

    return str(number)


def ordinal_to_words(number: int) -> str:
    if number in ORDINAL_TO_WORD:
        return ORDINAL_TO_WORD[number]
    if number < 1_000_000:
        if number < 100:
            return f"{number_to_words(number)}ster"

        cardinal = number_to_words(number)
        suffix_number = number % 100
        if suffix_number == 0:
            return f"{cardinal}ster"

        suffix_cardinal = number_to_words(suffix_number)
        if not cardinal.endswith(suffix_cardinal):
            return f"{cardinal}ster"

        return f"{cardinal[:-len(suffix_cardinal)]}{ordinal_to_words(suffix_number)}"
    return f"{number}."


def ordinal_dative(number: int) -> str:
    word = ordinal_to_words(number)
    if word.endswith("er"):
        return f"{word[:-2]}en"
    if word.endswith("ster"):
        return f"{word[:-2]}en"
    return word


def ordinal_weak(number: int) -> str:
    word = ordinal_to_words(number)
    return word[:-1] if word.endswith("er") else word


def year_to_words(year: str | int) -> str:
    year_int = int(year)
    if 2000 <= year_int < 2100:
        rest = year_int - 2000
        return "zweitausend" if rest == 0 else f"zweitausend{number_to_words(rest)}"
    return number_to_words(year_int) if year_int < 1_000_000 else str(year)


def decimal_to_words(raw_value: str) -> str:
    normalized = raw_value.replace(".", ",")
    if "," not in normalized:
        return number_to_words(int(normalized))

    integer_part, decimal_part = normalized.split(",", 1)
    integer_word = number_to_words(int(integer_part or "0"))
    decimal_words = " ".join(number_to_words(int(digit)) for digit in decimal_part if digit.isdigit())
    return f"{integer_word} komma {decimal_words}".strip()


def _number_value(raw: str) -> float | None:
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _number_word_with_gender(raw: str, gender: str | None) -> str:
    prefix = "minus " if raw.startswith("-") else ""
    unsigned = raw.lstrip("-")

    if re.fullmatch(r"0*1", unsigned):
        if gender == "f":
            return f"{prefix}eine"
        return f"{prefix}ein"

    return f"{prefix}{decimal_to_words(unsigned)}"


def _unit_form(raw: str, singular: str, plural: str) -> str:
    value = _number_value(raw)
    if value is not None and abs(value) == 1:
        return singular
    return plural


def _normalize_numbered_units(text: str) -> str:
    for unit_pattern, singular, plural, gender in NUMBERED_UNITS:
        def replace_unit(
            match: re.Match,
            _singular: str = singular,
            _plural: str = plural,
            _gender: str | None = gender,
        ) -> str:
            raw = match.group(1)
            number_word = _number_word_with_gender(raw, _gender)
            unit_word = _unit_form(raw, _singular, _plural)
            return f"{number_word} {unit_word}"

        if unit_pattern.endswith(r"\."):
            lookahead = r"(?=\s|[,!?]|$)"
        else:
            lookahead = r"(?=\b|[.,!?])"

        text = re.sub(
            rf"(?i)(?<!\w)(-?\d+(?:[,.]\d+)?)\s*{unit_pattern}{lookahead}",
            replace_unit,
            text,
        )

    return text


def _normalize_euro_amounts(text: str) -> str:
    def replace_euro_amount(match: re.Match[str]) -> str:
        euros_raw = match.group(1)
        cents_raw = match.group(2)
        euros_word = _number_word_with_gender(euros_raw, None)
        cents = int(cents_raw.ljust(2, "0")[:2])

        if cents == 0:
            return f"{euros_word} Euro"

        return f"{euros_word} Euro {number_to_words(cents)}"

    return re.sub(
        r"(?i)(?<!\w)(-?\d+)[,.](\d{1,2})\s*EUR\b",
        replace_euro_amount,
        text,
    )


def _protect_cardinal_label_numbers(text: str) -> str:
    """Read label numbers as cardinals, not ordinals, before sentence boundaries."""
    label_pattern = r"(Nummer|laufende\s+Nummer|Gleis|Kapitel|Absatz|Seite)"

    def replace_label_number(match: re.Match[str]) -> str:
        label = match.group(1)
        number = int(match.group(2))
        return f"{label} {number_to_words(number)}{CARDINAL_LABEL_DOT_PLACEHOLDER}"

    return re.sub(
        rf"(?i)\b{label_pattern}\s+(\d{{1,6}})\.(?=\s|$)",
        replace_label_number,
        text,
    )


def normalize_tts_text(text: str) -> str:
    """Make German assistant text easier for Kokoro/espeak to pronounce."""
    if not text:
        return text

    text = _normalize_euro_amounts(text)
    text = _normalize_numbered_units(text)

    for pattern, replacement in ABBREVIATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = _protect_cardinal_label_numbers(text)

    def replace_temperature(match: re.Match[str]) -> str:
        raw_value = match.group(1)
        prefix = "minus " if raw_value.startswith("-") else ""
        value = decimal_to_words(raw_value.lstrip("-"))
        return f"{prefix}{value} Grad Celsius"

    def replace_degree_without_unit(match: re.Match[str]) -> str:
        raw_value = match.group(1)
        prefix = "minus " if raw_value.startswith("-") else ""
        value = decimal_to_words(raw_value.lstrip("-"))
        return f"{prefix}{value} Grad"

    def replace_numeric_date(match: re.Match[str]) -> str:
        prefix = match.group(1) or ""
        day = int(match.group(2))
        month = int(match.group(3))
        year = match.group(4)

        result = f"{prefix}{ordinal_dative(day)} {ordinal_dative(month)}"
        if year:
            result += f" {year_to_words(year)}"
        return result

    def replace_text_date(match: re.Match[str]) -> str:
        prefix_full = match.group(1) or ""
        prefix = prefix_full.strip().lower()
        day = int(match.group(2))
        month = match.group(3)
        year = match.group(4)

        day_word = ordinal_to_words(day)
        if prefix in {"am", "den", "zum", "dem", "vom", "bis zum", "jeden"}:
            day_word = ordinal_dative(day)
        elif prefix in {"der", "die", "das"} and day_word.endswith("er"):
            day_word = day_word[:-1]

        result = f"{prefix_full}{day_word} {month}"
        if year:
            result += f" {year_to_words(year)}"
        return result

    def replace_time(match: re.Match[str]) -> str:
        hour = int(match.group(1))
        minute = int(match.group(2))
        hour_word = "ein" if hour == 1 else number_to_words(hour)
        if minute == 0:
            return f"{hour_word} Uhr"
        return f"{hour_word} Uhr {number_to_words(minute)}"

    def replace_ordinal(match: re.Match[str]) -> str:
        prefix_full = match.group(1) or ""
        prefix = prefix_full.strip().lower()
        number = int(match.group(2))

        if prefix.startswith("nach ") or prefix in {
            "am",
            "im",
            "zum",
            "vom",
            "dem",
            "den",
            "einen",
            "einem",
            "jeden",
            "jedem",
        }:
            word = ordinal_dative(number)
        elif prefix in {"der", "die", "das", "eine", "einer", "jede", "jeder"}:
            word = ordinal_weak(number)
        else:
            word = ordinal_to_words(number)

        return f"{prefix_full}{word}"

    text = re.sub(r"(?<!\w)(-?\d+(?:[,.]\d+)?)\s*°\s*[Cc]\b", replace_temperature, text)
    text = re.sub(r"(?<!\w)(-?\d+(?:[,.]\d+)?)\s*°(?!\s*[Cc]\b)", replace_degree_without_unit, text)
    text = re.sub(
        r"(?i)(?<!\w)(am\s+|den\s+|zum\s+|vom\s+|bis\s+zum\s+|jeden\s+)?"
        r"(\d{1,2})\.(\d{1,2})\.(?:\s*(20\d{2}))?(?=\s|[.,!?]|$)",
        replace_numeric_date,
        text,
    )
    text = re.sub(
        r"(?i)(?<!\w)(am\s+|der\s+|die\s+|das\s+|den\s+|zum\s+|vom\s+|dem\s+|bis\s+zum\s+|jeden\s+)?"
        r"(\d{1,2})\.\s*"
        + MONTHS
        + r"(?:\s+(20\d{2}))?(?=\s|[.,!?]|$)",
        replace_text_date,
        text,
    )
    text = re.sub(r"(?<!\w)(\d{1,2}):(\d{2})(?:\s*[Uu]hr)?(?=\s|[.,!?]|$)", replace_time, text)
    text = re.sub(
        r"(?i)(?<!\w)(am\s+|im\s+|zum\s+|vom\s+|dem\s+|den\s+|der\s+|die\s+|das\s+|"
        r"eine\s+|einer\s+|einen\s+|einem\s+|jeden\s+|jedem\s+|jede\s+|jeder\s+|"
        r"nach\s+der\s+(?:gefühlt\s+)?)?"
        r"(\d{1,6})\.(?=\s+\w|$)",
        replace_ordinal,
        text,
    )
    text = text.replace(CARDINAL_LABEL_DOT_PLACEHOLDER, ".")
    text = re.sub(r"(?i)\bHbf\b\.?", "Hauptbahnhof", text)
    text = re.sub(r"(?i)\bEUR\b", "Euro", text)

    return text
