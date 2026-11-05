"""Functional tests for target.py.

Every one of the 16 functions is covered for:
  * valid inputs (typical values),
  * boundary values (the exact edges of each rule),
  * invalid values (inputs the function rejects on purpose),
  * wrong types (inputs of a type the function was never meant to take).

Conventions used throughout:
  * Exceptions are asserted with the exact class via ``pytest.raises`` and, for
    messages that ``target.py`` defines itself, with ``match=`` on the full,
    escaped message. Built-in Python messages change between versions (for
    example 3.12 vs 3.14), so for those only a stable fragment is matched.
  * Booleans are compared with ``is`` so a truthy non-bool (1, "yes") fails.
  * Result types are checked wherever the type is part of the contract
    (int vs float, tuple vs list, set vs frozenset ...).
  * ``pytest.approx`` is used only where the result is an inexact float.
    Rounded or exactly representable results are compared with ``==``.
  * Tests marked "characterises current behaviour" pin down behaviour that is
    listed as a suspected bug in README.md, so any change is noticed.
"""

import inspect
import math
import re

import pytest

import target

# --------------------------------------------------------------------------- #
# 1. is_adult(age) -> bool
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, False),  # lower boundary of the valid range
        (1, False),
        (17, False),  # just below the adult boundary
        (18, True),  # exact boundary
        (19, True),  # just above the boundary
        (65, True),
        (150, True),
        (17.99, False),  # floats are compared numerically
        (18.0, True),
    ],
    ids=lambda v: repr(v),
)
def test_is_adult_returns_expected_bool(age, expected):
    result = target.is_adult(age)
    assert result is expected


@pytest.mark.parametrize("age", [-1, -18, -0.01, -1000])
def test_is_adult_negative_age_raises_value_error(age):
    with pytest.raises(ValueError, match=r"^age cannot be negative$"):
        target.is_adult(age)


@pytest.mark.parametrize("age", ["18", None, [18], (18,), {18: 18}])
def test_is_adult_wrong_type_raises_type_error(age):
    with pytest.raises(TypeError, match="not supported between instances of"):
        target.is_adult(age)


def test_is_adult_accepts_bool_characterises_current_behaviour():
    # bool is a subclass of int, so True is treated as age 1 (suspected bug).
    assert target.is_adult(True) is False
    assert target.is_adult(False) is False


# --------------------------------------------------------------------------- #
# 2. celsius_to_fahrenheit(celsius) -> float rounded to 2 decimals
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("celsius", "expected"),
    [
        (0, 32.0),  # freezing point
        (100, 212.0),  # boiling point
        (-40, -40.0),  # the scales meet
        (37, 98.6),  # body temperature (float noise removed by round)
        (36.6, 97.88),  # needs 2 decimals, not 1
        (1.234, 34.22),  # 34.2212 -> rounded down to 2 decimals
        (0.5, 32.9),
        (-17.78, -0.0),  # -0.004 rounds to -0.0
        (-273.15, -459.67),  # absolute zero
        (1000, 1832.0),
    ],
    ids=lambda v: repr(v),
)
def test_celsius_to_fahrenheit_valid(celsius, expected):
    result = target.celsius_to_fahrenheit(celsius)
    # round(..., 2) returns the float nearest to the 2-decimal value, so an
    # exact comparison is correct here and also catches "forgot to round".
    assert result == expected
    assert isinstance(result, float)


def test_celsius_to_fahrenheit_rounds_to_two_decimals():
    result = target.celsius_to_fahrenheit(21.111)  # 69.9998 before rounding
    assert result == 70.0
    assert result == round(result, 2)


def test_celsius_to_fahrenheit_special_floats():
    assert target.celsius_to_fahrenheit(math.inf) == math.inf
    assert target.celsius_to_fahrenheit(-math.inf) == -math.inf
    assert math.isnan(target.celsius_to_fahrenheit(math.nan))


@pytest.mark.parametrize(
    "celsius",
    ["abc", "", None, [1], (1,), {1}],
    ids=lambda v: repr(v),
)
def test_celsius_to_fahrenheit_wrong_type_raises_type_error(celsius):
    with pytest.raises(TypeError, match="unsupported operand type"):
        target.celsius_to_fahrenheit(celsius)


def test_celsius_to_fahrenheit_no_validation_characterises_current_behaviour():
    # Below absolute zero and bool are accepted without error (suspected bugs).
    assert target.celsius_to_fahrenheit(-300) == -508.0
    assert target.celsius_to_fahrenheit(True) == 33.8


# --------------------------------------------------------------------------- #
# 3. count_vowels(text) -> int
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),  # empty string boundary
        ("a", 1),  # single vowel
        ("b", 0),  # single consonant
        ("aeiou", 5),  # every vowel once
        ("AEIOU", 5),  # case is ignored
        ("AeIoU", 5),
        ("bcdfg", 0),
        ("y", 0),  # y is not a vowel
        ("rhythm", 0),
        ("Hello, World!", 3),
        ("queue", 4),  # repeated vowels are all counted
        ("12345 !?", 0),  # digits / punctuation
        ("   ", 0),
        ("Programming in Python", 5),
        ("aaaaaaaaaa" * 100, 1000),  # long input
    ],
    ids=lambda v: repr(v)[:30],
)
def test_count_vowels_valid(text, expected):
    result = target.count_vowels(text)
    assert result == expected
    assert type(result) is int


def test_count_vowels_only_ascii_vowels_characterises_current_behaviour():
    # Accented vowels are not counted (documented as suspected bug).
    assert target.count_vowels("éàü") == 0
    assert target.count_vowels("café") == 1


@pytest.mark.parametrize(
    "text",
    [None, 123, 1.5, True, ["a", "e"], ("a",), {"a"}, b"aeiou"],
    ids=lambda v: repr(v),
)
def test_count_vowels_wrong_type_raises_type_error(text):
    with pytest.raises(TypeError, match=r"^text must be a string$"):
        target.count_vowels(text)


# --------------------------------------------------------------------------- #
# 4. invert(flag) -> bool
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("flag", "expected"), [(True, False), (False, True)])
def test_invert_valid(flag, expected):
    assert target.invert(flag) is expected


def test_invert_twice_returns_original():
    assert target.invert(target.invert(True)) is True
    assert target.invert(target.invert(False)) is False


@pytest.mark.parametrize(
    "flag",
    [0, 1, -1, 0.0, 1.0, "True", "False", "", None, [], [True], {}],
    ids=lambda v: repr(v),
)
def test_invert_non_bool_raises_type_error(flag):
    with pytest.raises(TypeError, match=r"^flag must be True or False$"):
        target.invert(flag)


# --------------------------------------------------------------------------- #
# 5. greet(name=None) -> str
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Alice", "Hello, Alice!"),
        ("Bob", "Hello, Bob!"),
        ("A", "Hello, A!"),  # shortest real name
        ("  Bob  ", "Hello, Bob!"),  # surrounding spaces are stripped
        ("\tCarol\n", "Hello, Carol!"),  # any surrounding whitespace
        ("Mary Jane", "Hello, Mary Jane!"),  # inner spaces are kept
        ("guest", "Hello, guest!"),
        ("Zoë", "Hello, Zoë!"),
    ],
    ids=lambda v: repr(v),
)
def test_greet_with_name(name, expected):
    result = target.greet(name)
    assert result == expected
    assert isinstance(result, str)


@pytest.mark.parametrize(
    "name",
    [None, "", " ", "     ", "\t", "\n", " \t\n "],
    ids=lambda v: repr(v),
)
def test_greet_falls_back_to_guest(name):
    assert target.greet(name) == "Hello, Guest!"


def test_greet_default_argument_is_guest():
    assert target.greet() == "Hello, Guest!"
    default = inspect.signature(target.greet).parameters["name"].default
    assert default is None


@pytest.mark.parametrize("name", [123, 1.5, True, ["Alice"], ("Alice",)])
def test_greet_non_string_raises_attribute_error(name):
    # A non-string name is not validated: the .strip() call fails with
    # AttributeError instead of a TypeError (listed as a suspected bug).
    with pytest.raises(AttributeError, match="has no attribute 'strip'"):
        target.greet(name)


# --------------------------------------------------------------------------- #
# 6. find_max(numbers) -> largest item
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("numbers", "expected"),
    [
        ([7], 7),  # single element boundary
        ([1, 2, 3], 3),  # max at the end
        ([3, 2, 1], 3),  # max at the start
        ([2, 9, 4], 9),  # max in the middle
        ([-5, -2, -9], -2),  # all negative (a "start from 0" bug fails)
        ([0, 0, 0], 0),
        ([5, 5, 1], 5),  # duplicated maximum
        ([1.5, 1.25, 1.75], 1.75),
        ([1, 2.5, 2], 2.5),  # mixed int and float
        ([10**20, 1], 10**20),  # very large int
        ([-math.inf, -1e308], -1e308),
        ((4, 8, 6), 8),  # a tuple also works
    ],
    ids=lambda v: repr(v),
)
def test_find_max_valid(numbers, expected):
    result = target.find_max(numbers)
    assert result == expected
    assert type(result) is type(expected)


def test_find_max_does_not_modify_input():
    numbers = [3, 1, 2]
    target.find_max(numbers)
    assert numbers == [3, 1, 2]


@pytest.mark.parametrize("numbers", [[], (), ""], ids=lambda v: repr(v))
def test_find_max_empty_raises_value_error(numbers):
    with pytest.raises(ValueError, match=r"^list is empty$"):
        target.find_max(numbers)


@pytest.mark.parametrize(
    ("numbers", "fragment"),
    [
        (None, "has no len"),
        (5, "has no len"),
        ((x for x in [1, 2]), "has no len"),
        ([1, "a"], "not supported between instances of"),
        ([1, None], "not supported between instances of"),
    ],
    ids=["None", "int", "generator", "int-and-str", "int-and-None"],
)
def test_find_max_wrong_type_raises_type_error(numbers, fragment):
    with pytest.raises(TypeError, match=fragment):
        target.find_max(numbers)


def test_find_max_accepts_any_sized_iterable_characterises_current_behaviour():
    assert target.find_max("abc") == "c"
    assert target.find_max({3, 9, 1}) == 9


# --------------------------------------------------------------------------- #
# 7. get_price(prices, item) -> price
# --------------------------------------------------------------------------- #

PRICES = {"apple": 1.25, "bread": 2, "water": 0, "caviar": 999.99}


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ("apple", 1.25),
        ("bread", 2),
        ("water", 0),  # falsy price must still be returned, not "missing"
        ("caviar", 999.99),
    ],
)
def test_get_price_existing_item(item, expected):
    result = target.get_price(PRICES, item)
    assert result == expected
    assert type(result) is type(expected)


def test_get_price_returns_stored_object_unchanged():
    price = object()
    assert target.get_price({"x": price}, "x") is price


def test_get_price_stored_none_is_returned_not_treated_as_missing():
    assert target.get_price({"free": None}, "free") is None


def test_get_price_non_string_keys():
    assert target.get_price({1: "one", None: "none", (1, 2): "pair"}, 1) == "one"
    assert target.get_price({None: "none"}, None) == "none"
    assert target.get_price({(1, 2): "pair"}, (1, 2)) == "pair"


def test_get_price_does_not_modify_dictionary():
    prices = {"apple": 1}
    target.get_price(prices, "apple")
    assert prices == {"apple": 1}


@pytest.mark.parametrize(
    ("prices", "item"),
    [
        (PRICES, "banana"),  # missing item
        (PRICES, "Apple"),  # keys are case-sensitive
        (PRICES, " apple"),  # no whitespace normalisation
        (PRICES, ""),
        ({}, "apple"),  # empty dictionary
    ],
    ids=["missing", "case", "whitespace", "empty-key", "empty-dict"],
)
def test_get_price_missing_item_raises_key_error(prices, item):
    with pytest.raises(KeyError, match=re.escape(f"{item} not found")) as info:
        target.get_price(prices, item)
    assert info.value.args == (f"{item} not found",)


@pytest.mark.parametrize(
    ("prices", "item", "fragment"),
    [
        (None, "apple", "argument of type 'NoneType' is not"),
        (5, "apple", "argument of type 'int' is not"),
        ({}, ["apple"], "unhashable type"),
        (["apple"], "apple", "list indices must be integers"),
    ],
    ids=["None-prices", "int-prices", "unhashable-item", "list-prices"],
)
def test_get_price_wrong_type_raises_type_error(prices, item, fragment):
    with pytest.raises(TypeError, match=fragment):
        target.get_price(prices, item)


# --------------------------------------------------------------------------- #
# 8. swap(pair) -> tuple of the two values swapped
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("pair", "expected"),
    [
        ((1, 2), (2, 1)),
        (("a", "b"), ("b", "a")),
        ((5, 5), (5, 5)),  # equal values
        ((None, 0), (0, None)),
        ((1, "x"), ("x", 1)),  # mixed types
        (([1], {2}), ({2}, [1])),
        ([1, 2], (2, 1)),  # a list in -> a tuple out
    ],
    ids=lambda v: repr(v),
)
def test_swap_valid(pair, expected):
    result = target.swap(pair)
    assert result == expected
    assert type(result) is tuple


def test_swap_twice_returns_original_values():
    assert target.swap(target.swap((1, 2))) == (1, 2)


def test_swap_keeps_object_identity():
    first, second = object(), object()
    assert target.swap((first, second))[0] is second
    assert target.swap((first, second))[1] is first


@pytest.mark.parametrize(
    "pair",
    [(), (1,), (1, 2, 3), (1, 2, 3, 4), [], [1], "", "abc"],
    ids=lambda v: repr(v),
)
def test_swap_wrong_length_raises_value_error(pair):
    with pytest.raises(ValueError, match=r"^pair must have exactly 2 values$"):
        target.swap(pair)


@pytest.mark.parametrize(
    ("pair", "fragment"),
    [
        (None, "has no len"),
        (12, "has no len"),
        ({1, 2}, "not subscriptable"),
    ],
    ids=["None", "int", "set"],
)
def test_swap_wrong_type_raises_type_error(pair, fragment):
    with pytest.raises(TypeError, match=fragment):
        target.swap(pair)


def test_swap_accepts_two_char_string_characterises_current_behaviour():
    assert target.swap("ab") == ("b", "a")
    with pytest.raises(KeyError):  # a 2-key dict leaks a KeyError
        target.swap({"a": 1, "b": 2})


# --------------------------------------------------------------------------- #
# 9. common_items(set_a, set_b) -> set intersection
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("set_a", "set_b", "expected"),
    [
        ({1, 2, 3}, {2, 3, 4}, {2, 3}),  # partial overlap
        ({1, 2}, {3, 4}, set()),  # disjoint
        ({1, 2}, {1, 2}, {1, 2}),  # identical
        ({1, 2, 3}, {2}, {2}),  # subset
        (set(), {1, 2}, set()),  # one empty
        (set(), set(), set()),  # both empty
        ({"a", "b"}, {"b", "c"}, {"b"}),
        ({1, 2.0, "x"}, {2, "x"}, {2.0, "x"}),  # 2 == 2.0
        ({(1, 2), None}, {None}, {None}),
    ],
    ids=lambda v: repr(v),
)
def test_common_items_valid(set_a, set_b, expected):
    result = target.common_items(set_a, set_b)
    assert result == expected
    assert type(result) is set


def test_common_items_is_symmetric():
    a, b = {1, 2, 3}, {3, 4, 1}
    assert target.common_items(a, b) == target.common_items(b, a) == {1, 3}


def test_common_items_does_not_modify_inputs():
    a, b = {1, 2}, {2, 3}
    target.common_items(a, b)
    assert a == {1, 2}
    assert b == {2, 3}


def test_common_items_frozenset_returns_frozenset():
    result = target.common_items(frozenset({1, 2}), frozenset({2, 3}))
    assert result == frozenset({2})
    assert type(result) is frozenset


@pytest.mark.parametrize(
    ("set_a", "set_b"),
    [
        ([1, 2], [2, 3]),
        ({1, 2}, [2]),
        ((1, 2), {2}),
        (None, {1}),
        ({1}, None),
        ("ab", "bc"),
    ],
    ids=["lists", "set-list", "tuple-set", "None-set", "set-None", "strings"],
)
def test_common_items_wrong_type_raises_type_error(set_a, set_b):
    with pytest.raises(TypeError, match="unsupported operand type"):
        target.common_items(set_a, set_b)


# --------------------------------------------------------------------------- #
# 10. is_leap_year(year) -> bool
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (1, False),  # lowest valid year
        (4, True),  # first leap year
        (100, False),  # divisible by 100, not 400
        (400, True),  # divisible by 400
        (1900, False),
        (1996, True),
        (1999, False),
        (2000, True),
        (2023, False),
        (2024, True),
        (2100, False),
        (2400, True),
        (2401, False),
        (9996, True),
    ],
)
def test_is_leap_year_valid(year, expected):
    assert target.is_leap_year(year) is expected


@pytest.mark.parametrize("year", [0, -1, -4, -400, -2000])
def test_is_leap_year_below_one_raises_value_error(year):
    with pytest.raises(ValueError, match=r"^year must be 1 or more$"):
        target.is_leap_year(year)


@pytest.mark.parametrize("year", ["2024", None, [2024], (2024,)])
def test_is_leap_year_wrong_type_raises_type_error(year):
    with pytest.raises(TypeError, match="not supported between instances of"):
        target.is_leap_year(year)


def test_is_leap_year_accepts_float_and_bool_characterises_current_behaviour():
    assert target.is_leap_year(2000.0) is True
    assert target.is_leap_year(True) is False  # True == year 1


# --------------------------------------------------------------------------- #
# 11. to_int(value) -> int
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, 0),
        (42, 42),
        (-7, -7),
        ("42", 42),
        ("-7", -7),
        ("+5", 5),
        ("  42  ", 42),  # int() strips whitespace
        ("007", 7),
        ("1_000", 1000),
        (3.0, 3),
        (3.9, 3),  # truncates toward zero, does not round
        (-3.9, -3),  # truncates toward zero, does not floor
        (0.999, 0),
        (-0.5, 0),
        (10**30, 10**30),
        (b"12", 12),
    ],
    ids=lambda v: repr(v),
)
def test_to_int_valid(value, expected):
    result = target.to_int(value)
    assert result == expected
    assert type(result) is int


@pytest.mark.parametrize("value", [True, False])
def test_to_int_bool_raises_type_error(value):
    with pytest.raises(TypeError, match=r"^bool is not allowed$"):
        target.to_int(value)


@pytest.mark.parametrize(
    "value",
    ["abc", "", "  ", "3.5", "1e3", "12abc", "four", math.nan],
    ids=lambda v: repr(v),
)
def test_to_int_invalid_value_raises_value_error(value):
    with pytest.raises(ValueError):
        target.to_int(value)


def test_to_int_invalid_literal_message():
    with pytest.raises(ValueError, match="invalid literal for int"):
        target.to_int("abc")


@pytest.mark.parametrize("value", [math.inf, -math.inf])
def test_to_int_infinity_raises_overflow_error(value):
    with pytest.raises(OverflowError, match="cannot convert float infinity"):
        target.to_int(value)


@pytest.mark.parametrize("value", [None, [1], (1,), {1: 1}, 1j])
def test_to_int_wrong_type_raises_type_error(value):
    with pytest.raises(TypeError, match=r"int\(\) argument must be"):
        target.to_int(value)
