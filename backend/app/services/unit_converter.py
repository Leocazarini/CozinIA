"""Converts an ingredient's quantity and unit from US/imperial measurements
into the metric units used in Brazil — the deterministic half of recipe
translation (see recipe_translator.py for the half that needs judgement:
translating prose, and rewriting measurements mentioned inline in free
text).

Kept pure and separate for the same reason video_captions.py is split from
video_source.py: arithmetic is worth pinning down and tested exhaustively,
without an AI response in the way.

Only handles the unit vocabulary a recipe written in English is likely to
use (oz, lb, cup, tbsp, tsp, °F, in, and their common variants) — that
covers the overwhelming majority of non-Portuguese recipe content this app
sees. A unit outside that vocabulary (whether it's already metric, a count
like "unidades", or a word from some other language) is returned unchanged;
recipe_translator.py falls back to the AI's own translation of it in that
case.
"""

import re

# Every factor converts one unit of the source into its base metric unit
# (grams for weight, milliliters for volume) — from there, _render_scaled
# decides whether the result is small enough to stay in that unit or should
# switch to the larger one (kg, L).
_GRAM_FACTORS: dict[str, float] = {
    "oz": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
    "lb": 453.592,
    "lbs": 453.592,
    "pound": 453.592,
    "pounds": 453.592,
}

_MILLILITER_FACTORS: dict[str, float] = {
    "fl oz": 29.5735,
    "floz": 29.5735,
    "fluid ounce": 29.5735,
    "fluid ounces": 29.5735,
    "cup": 240.0,
    "cups": 240.0,
    "tbsp": 14.7868,
    "tbs": 14.7868,
    "tablespoon": 14.7868,
    "tablespoons": 14.7868,
    "tsp": 4.92892,
    "teaspoon": 4.92892,
    "teaspoons": 4.92892,
    "pint": 473.176,
    "pints": 473.176,
    "quart": 946.353,
    "quarts": 946.353,
    "gallon": 3785.41,
    "gallons": 3785.41,
}

_CENTIMETER_FACTORS: dict[str, float] = {
    "in": 2.54,
    "inch": 2.54,
    "inches": 2.54,
    '"': 2.54,
}

_FAHRENHEIT_UNITS = frozenset({"f", "°f", "fahrenheit"})

_UNICODE_FRACTIONS: dict[str, float] = {
    "¼": 1 / 4,
    "½": 1 / 2,
    "¾": 3 / 4,
    "⅓": 1 / 3,
    "⅔": 2 / 3,
    "⅕": 1 / 5,
    "⅖": 2 / 5,
    "⅗": 3 / 5,
    "⅘": 4 / 5,
    "⅙": 1 / 6,
    "⅚": 5 / 6,
    "⅛": 1 / 8,
    "⅜": 3 / 8,
    "⅝": 5 / 8,
    "⅞": 7 / 8,
}

# Tried in this order against the whole string before any range-splitting is
# attempted — see the module docstring on _parse_quantity for why that order
# matters ("1-1/2" is a mixed number, not a range).
_MIXED_HYPHEN_RE = re.compile(r"^(\d+)-(\d+)/(\d+)$")
_MIXED_SPACE_RE = re.compile(r"^(\d+)\s+(\d+)/(\d+)$")
_FRACTION_RE = re.compile(r"^(\d+)/(\d+)$")
_DECIMAL_RE = re.compile(r"^\d+(?:[.,]\d+)?$")
_RANGE_RE = re.compile(r"^(.+?)\s*(?:-|–|to)\s*(.+)$", re.IGNORECASE)


def convert_measurement(quantity: str | None, unit: str | None) -> tuple[str | None, str | None]:
    """Convert `quantity`/`unit` to Brazilian metric units when `unit` is a
    recognised US/imperial one and `quantity` parses as a number (or a
    range of two numbers). Otherwise returns both unchanged, exactly as
    given — never a guess.
    """
    if quantity is None or unit is None:
        return quantity, unit

    amount = _parse_quantity(quantity)
    if amount is None:
        return quantity, unit

    normalized_unit = _normalize_unit(unit)

    if normalized_unit in _GRAM_FACTORS:
        return _render_scaled(
            amount,
            _GRAM_FACTORS[normalized_unit],
            small_unit="g",
            small_decimals=0,
            large_unit="kg",
            large_decimals=2,
        )
    if normalized_unit in _MILLILITER_FACTORS:
        return _render_scaled(
            amount,
            _MILLILITER_FACTORS[normalized_unit],
            small_unit="ml",
            small_decimals=0,
            large_unit="L",
            large_decimals=2,
        )
    if normalized_unit in _CENTIMETER_FACTORS:
        return _render_scaled(
            amount,
            _CENTIMETER_FACTORS[normalized_unit],
            small_unit="cm",
            small_decimals=1,
            large_unit=None,
            large_decimals=0,
        )
    if normalized_unit in _FAHRENHEIT_UNITS:
        return _render_temperature(amount)

    return quantity, unit


def _normalize_unit(unit: str) -> str:
    """Lowercase, drop periods ("Tbsp." / "fl. oz."), and collapse
    whitespace, so every written variant of a unit maps to the same key."""
    return " ".join(unit.strip().lower().replace(".", "").split())


def _parse_quantity(text: str) -> float | tuple[float, float] | None:
    """Parse a quantity as written in a recipe: a plain number, a fraction,
    a mixed number, or a range of two of those. Returns None for anything
    that doesn't parse as one — e.g. "a pinch" — so the caller can leave it
    untouched instead of guessing.

    A single value is always tried before splitting as a range: "1-1/2" is
    a mixed number (one and a half), not the range "1 to 1/2", and only
    trying the range split after a whole-string parse has failed keeps that
    read correct.
    """
    single = _parse_single(text)
    if single is not None:
        return single

    match = _RANGE_RE.match(text.strip())
    if match is None:
        return None
    low = _parse_single(match.group(1))
    high = _parse_single(match.group(2))
    if low is None or high is None:
        return None
    return low, high


def _parse_single(text: str) -> float | None:
    """Parse one number: integer, decimal (dot or comma), simple fraction,
    mixed number (space- or hyphen-separated), or a unicode fraction
    character optionally preceded by a whole number."""
    text = text.strip()
    if not text:
        return None

    if text in _UNICODE_FRACTIONS:
        return _UNICODE_FRACTIONS[text]
    last_char = text[-1]
    if last_char in _UNICODE_FRACTIONS:
        whole = text[:-1].strip()
        if whole.isdigit():
            return float(whole) + _UNICODE_FRACTIONS[last_char]
        return None

    if match := (_MIXED_HYPHEN_RE.match(text) or _MIXED_SPACE_RE.match(text)):
        whole, numerator, denominator = match.groups()
        return _mixed_number(whole, numerator, denominator)

    if match := _FRACTION_RE.match(text):
        numerator, denominator = match.groups()
        return _fraction(numerator, denominator)

    if _DECIMAL_RE.match(text):
        return float(text.replace(",", "."))

    return None


def _mixed_number(whole: str, numerator: str, denominator: str) -> float | None:
    fraction = _fraction(numerator, denominator)
    return None if fraction is None else int(whole) + fraction


def _fraction(numerator: str, denominator: str) -> float | None:
    denominator_value = int(denominator)
    return None if denominator_value == 0 else int(numerator) / denominator_value


def _render_scaled(
    amount: float | tuple[float, float],
    factor: float,
    *,
    small_unit: str,
    small_decimals: int,
    large_unit: str | None,
    large_decimals: int,
) -> tuple[str, str]:
    """Multiply `amount` by `factor` and format the result, switching from
    `small_unit` to `large_unit` once the converted value reaches 1000 —
    the way a Brazilian recipe writes "720ml" but "1.2L". Both ends of a
    range are rendered in whichever unit the larger end needs, so a range
    never mixes units. `large_unit=None` means this unit never switches
    (length stays in cm regardless of size)."""
    converted = (
        tuple(value * factor for value in amount) if isinstance(amount, tuple) else amount * factor
    )
    highest = max(converted) if isinstance(converted, tuple) else converted

    if large_unit is not None and highest >= 1000:
        unit_label, decimals, divisor = large_unit, large_decimals, 1000
    else:
        unit_label, decimals, divisor = small_unit, small_decimals, 1

    if isinstance(converted, tuple):
        text = "-".join(_format_number(value / divisor, decimals) for value in converted)
    else:
        text = _format_number(converted / divisor, decimals)
    return text, unit_label


def _render_temperature(amount: float | tuple[float, float]) -> tuple[str, str]:
    def to_celsius(fahrenheit: float) -> float:
        return (fahrenheit - 32) * 5 / 9

    if isinstance(amount, tuple):
        text = "-".join(_format_number(to_celsius(value), 0) for value in amount)
    else:
        text = _format_number(to_celsius(amount), 0)
    return text, "°C"


def _format_number(value: float, decimals: int) -> str:
    """Round to `decimals` places, then drop a trailing ".0"/".00" — 227,
    not 227.0; 1.5, not 1.50."""
    rounded = round(value, decimals)
    if decimals == 0:
        return str(int(rounded))
    text = f"{rounded:.{decimals}f}".rstrip("0").rstrip(".")
    return text or "0"
