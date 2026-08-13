"""Specifications for unit_converter, the deterministic half of recipe
translation: turning a US/imperial ingredient quantity + unit into the
metric units used in Brazil.

Kept pure and tested in isolation from the AI call (see
recipe_translator.py) for the same reason video_captions.py is split from
video_source.py — arithmetic is worth pinning down exhaustively, without a
model response in the way.
"""

from app.services.unit_converter import convert_measurement


def test_given_ounces_when_converting_then_returns_grams() -> None:
    """Given a weight in ounces, when converted, then it comes back in
    whole grams."""
    quantity, unit = convert_measurement("8", "oz")

    assert (quantity, unit) == ("227", "g")


def test_given_pounds_under_a_kilo_when_converting_then_returns_grams() -> None:
    """Given a weight in pounds that converts to under 1000g, when
    converted, then it stays in grams rather than switching to kilograms."""
    quantity, unit = convert_measurement("0.5", "lb")

    assert (quantity, unit) == ("227", "g")


def test_given_pounds_over_a_kilo_when_converting_then_returns_kilograms() -> None:
    """Given a weight in pounds that converts to 1000g or more, when
    converted, then it switches to kilograms — the way a Brazilian recipe
    would write it — rounded to two decimals."""
    quantity, unit = convert_measurement("3", "lb")

    assert (quantity, unit) == ("1.36", "kg")


def test_given_cups_when_converting_then_returns_milliliters() -> None:
    """Given a volume in cups, when converted, then it comes back in
    whole milliliters."""
    quantity, unit = convert_measurement("1", "cup")

    assert (quantity, unit) == ("240", "ml")


def test_given_tablespoons_when_converting_then_returns_milliliters() -> None:
    """Given a volume in tablespoons, when converted, then it comes back in
    milliliters."""
    quantity, unit = convert_measurement("1", "tbsp")

    assert (quantity, unit) == ("15", "ml")


def test_given_teaspoons_when_converting_then_returns_milliliters() -> None:
    """Given a volume in teaspoons, when converted, then it comes back in
    milliliters."""
    quantity, unit = convert_measurement("1", "tsp")

    assert (quantity, unit) == ("5", "ml")


def test_given_a_volume_over_a_liter_when_converting_then_returns_liters() -> None:
    """Given a volume that converts to 1000ml or more, when converted, then
    it switches to liters, rounded to two decimals."""
    quantity, unit = convert_measurement("1", "gallon")

    assert (quantity, unit) == ("3.79", "L")


def test_given_fahrenheit_when_converting_then_returns_celsius() -> None:
    """Given an oven temperature in Fahrenheit, when converted, then it
    comes back in whole degrees Celsius."""
    quantity, unit = convert_measurement("350", "F")

    assert (quantity, unit) == ("177", "°C")


def test_given_inches_when_converting_then_returns_centimeters() -> None:
    """Given a length in inches (e.g. a pan size), when converted, then it
    comes back in centimeters, to one decimal place."""
    quantity, unit = convert_measurement("8", "inch")

    assert (quantity, unit) == ("20.3", "cm")


def test_given_a_simple_fraction_when_converting_then_the_fraction_is_resolved() -> None:
    """Given a quantity written as a simple fraction, when converted, then
    it is parsed as that fraction of the unit before converting."""
    quantity, unit = convert_measurement("1/2", "cup")

    assert (quantity, unit) == ("120", "ml")


def test_given_a_mixed_number_when_converting_then_the_fraction_is_resolved() -> None:
    """Given a quantity written as a mixed number (whole + fraction, space
    separated), when converted, then both parts are combined before
    converting."""
    quantity, unit = convert_measurement("1 1/2", "cups")

    assert (quantity, unit) == ("360", "ml")


def test_given_a_hyphenated_mixed_number_when_converting_then_it_is_not_mistaken_for_a_range() -> (
    None
):
    """Given a quantity written as a mixed number with a hyphen instead of a
    space (a common US recipe convention), when converted, then it is read
    as one number — not misread as a "1 to 2" range."""
    quantity, unit = convert_measurement("1-1/2", "cups")

    assert (quantity, unit) == ("360", "ml")


def test_given_a_range_when_converting_then_both_ends_are_converted() -> None:
    """Given a quantity written as a range, when converted, then both ends
    are converted and rendered in the same unit."""
    quantity, unit = convert_measurement("2-3", "tbsp")

    assert (quantity, unit) == ("30-44", "ml")


def test_given_a_worded_range_when_converting_then_both_ends_are_converted() -> None:
    """Given a quantity written as "x to y", when converted, then it is
    read the same way as a hyphenated range."""
    quantity, unit = convert_measurement("2 to 3", "tbsp")

    assert (quantity, unit) == ("30-44", "ml")


def test_given_an_already_metric_unit_when_converting_then_it_is_left_unchanged() -> None:
    """Given a unit that is already metric, when converted, then the
    quantity and unit are returned unchanged — there is nothing to do."""
    quantity, unit = convert_measurement("500", "g")

    assert (quantity, unit) == ("500", "g")


def test_given_a_count_based_unit_when_converting_then_it_is_left_unchanged() -> None:
    """Given a unit that names a count rather than a measurement (e.g.
    "unidades"), when converted, then it is returned unchanged — converting
    it would be meaningless."""
    quantity, unit = convert_measurement("3", "unidades")

    assert (quantity, unit) == ("3", "unidades")


def test_given_no_unit_when_converting_then_the_quantity_is_left_unchanged() -> None:
    """Given an ingredient with a quantity but no unit, when converted, then
    nothing changes — there is no unit to interpret."""
    quantity, unit = convert_measurement("3", None)

    assert (quantity, unit) == ("3", None)


def test_given_no_quantity_when_converting_then_the_unit_is_left_unchanged() -> None:
    """Given an ingredient with a unit but no quantity (e.g. "a gosto"),
    when converted, then nothing changes — there is no number to convert."""
    quantity, unit = convert_measurement(None, "oz")

    assert (quantity, unit) == (None, "oz")


def test_given_a_non_numeric_quantity_when_converting_then_it_is_left_unchanged() -> None:
    """Given a quantity that isn't a number the parser recognises (e.g. "a
    pinch"), when converted with a recognised unit, then it is left
    unchanged rather than guessed at."""
    quantity, unit = convert_measurement("a pinch", "oz")

    assert (quantity, unit) == ("a pinch", "oz")


def test_given_mixed_case_and_punctuation_in_the_unit_when_converting_then_it_still_matches() -> (
    None
):
    """Given a unit written with different casing and a trailing period
    (e.g. "Tbsp."), when converted, then it is recognised the same as its
    canonical form."""
    quantity, unit = convert_measurement("1", "Tbsp.")

    assert (quantity, unit) == ("15", "ml")


def test_given_fluid_ounces_when_converting_then_they_are_treated_as_volume_not_weight() -> (
    None
):
    """Given a quantity in fluid ounces, when converted, then it is treated
    as a volume (milliliters) — distinct from plain ounces, which are a
    weight."""
    quantity, unit = convert_measurement("8", "fl oz")

    assert (quantity, unit) == ("237", "ml")
