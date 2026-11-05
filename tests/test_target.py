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


# --------------------------------------------------------------------------- #
# 12. divide(a, b) -> float
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (10, 2, 5.0),
        (7, 2, 3.5),  # true division, not floor division
        (-9, 3, -3.0),
        (9, -3, -3.0),
        (-9, -3, 3.0),
        (0, 5, 0.0),  # zero numerator is fine
        (1, 4, 0.25),
        (5, 0.5, 10.0),
        (1, 1e-3, 1000.0),  # tiny non-zero divisor is allowed
        (2.5, 2.5, 1.0),
    ],
    ids=lambda v: repr(v),
)
def test_divide_exact_results(a, b, expected):
    result = target.divide(a, b)
    assert result == expected
    assert type(result) is float


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [(1, 3, 0.3333333333333333), (2, 3, 0.6666666666666666), (0.1, 0.3, 1 / 3)],
)
def test_divide_inexact_results(a, b, expected):
    assert target.divide(a, b) == pytest.approx(expected)


def test_divide_argument_order_matters():
    assert target.divide(10, 2) == 5.0
    assert target.divide(2, 10) == 0.2


@pytest.mark.parametrize(
    ("a", "b"),
    [(1, 0), (0, 0), (-5, 0), (1, 0.0), (1, -0.0), (1, False)],
    ids=lambda v: repr(v),
)
def test_divide_by_zero_raises_zero_division_error(a, b):
    with pytest.raises(ZeroDivisionError, match=r"^cannot divide by zero$"):
        target.divide(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [("10", 2), (10, "2"), (None, 1), (1, None), ([1], 1)],
    ids=lambda v: repr(v),
)
def test_divide_wrong_type_raises_type_error(a, b):
    with pytest.raises(TypeError, match="unsupported operand type"):
        target.divide(a, b)


# --------------------------------------------------------------------------- #
# 13. power(base, exponent)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("base", "exponent", "expected"),
    [
        (2, 3, 8),  # 3 ** 2 would be 9, 2 * 3 would be 6
        (3, 2, 9),
        (2, 0, 1),  # anything to the 0 is 1
        (0, 0, 1),  # Python defines 0 ** 0 == 1
        (0, 5, 0),
        (1, 1000, 1),
        (-2, 3, -8),  # odd exponent keeps the sign
        (-2, 2, 4),  # even exponent removes it
        (10, 1, 10),
        (2, 100, 2**100),  # exact big int
    ],
    ids=lambda v: repr(v),
)
def test_power_integer_results(base, exponent, expected):
    result = target.power(base, exponent)
    assert result == expected
    assert type(result) is int


@pytest.mark.parametrize(
    ("base", "exponent", "expected"),
    [
        (2, -1, 0.5),  # negative exponent -> float
        (2, -2, 0.25),
        (4, 0.5, 2.0),  # fractional exponent = root
        (2.5, 2, 6.25),
        (9, 0.5, 3.0),
        (10, -3, 0.001),
    ],
    ids=lambda v: repr(v),
)
def test_power_float_results(base, exponent, expected):
    result = target.power(base, exponent)
    assert result == pytest.approx(expected)
    assert type(result) is float


def test_power_inexact_result():
    assert target.power(2, 0.5) == pytest.approx(math.sqrt(2))


@pytest.mark.parametrize(("base", "exponent"), [(0, -1), (0.0, -2)])
def test_power_zero_to_negative_raises_zero_division_error(base, exponent):
    with pytest.raises(ZeroDivisionError, match="negative power"):
        target.power(base, exponent)


def test_power_float_overflow_raises_overflow_error():
    with pytest.raises(OverflowError):
        target.power(10.0, 400)


def test_power_negative_base_fractional_exponent_characterises_current_behaviour():
    result = target.power(-8, 1 / 3)
    assert type(result) is complex  # not -2.0 (suspected bug)
    assert result == pytest.approx(complex(1, math.sqrt(3)))


@pytest.mark.parametrize(
    ("base", "exponent"),
    [("2", 3), (2, "3"), (None, 2), (2, None), ([2], 2)],
    ids=lambda v: repr(v),
)
def test_power_wrong_type_raises_type_error(base, exponent):
    with pytest.raises(TypeError, match="unsupported operand type"):
        target.power(base, exponent)


# --------------------------------------------------------------------------- #
# 14. square_root(x) -> float
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("x", "expected"),
    [
        (0, 0.0),  # boundary: zero is allowed
        (1, 1.0),
        (4, 2.0),
        (9, 3.0),
        (0.25, 0.5),
        (2.25, 1.5),
        (10**10, 100000.0),
    ],
    ids=lambda v: repr(v),
)
def test_square_root_exact_results(x, expected):
    result = target.square_root(x)
    assert result == expected
    assert type(result) is float


@pytest.mark.parametrize("x", [2, 3, 0.5, 10, 12345.678])
def test_square_root_inexact_results(x):
    result = target.square_root(x)
    assert result == pytest.approx(x**0.5)
    assert result * result == pytest.approx(x)


def test_square_root_special_floats():
    assert target.square_root(math.inf) == math.inf
    assert math.isnan(target.square_root(math.nan))


def test_square_root_negative_zero_characterises_current_behaviour():
    result = target.square_root(-0.0)
    assert result == 0.0
    assert math.copysign(1.0, result) == -1.0  # sign of -0.0 leaks through


@pytest.mark.parametrize("x", [-1, -4, -0.0001, -1e-300, -math.inf])
def test_square_root_negative_raises_value_error(x):
    with pytest.raises(
        ValueError, match=r"^cannot take the square root of a negative number$"
    ):
        target.square_root(x)


@pytest.mark.parametrize("x", ["4", None, [4], 4j])
def test_square_root_wrong_type_raises_type_error(x):
    with pytest.raises(TypeError, match="not supported between instances of"):
        target.square_root(x)


# --------------------------------------------------------------------------- #
# 15. factorial(n) -> int
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (0, 1),  # boundary: 0! == 1
        (1, 1),
        (2, 2),
        (3, 6),
        (5, 120),
        (10, 3628800),
        (20, 2432902008176640000),
    ],
)
def test_factorial_known_values(n, expected):
    result = target.factorial(n)
    assert result == expected
    assert type(result) is int


@pytest.mark.parametrize("n", range(0, 31))
def test_factorial_matches_math_factorial(n):
    assert target.factorial(n) == math.factorial(n)


def test_factorial_large_input_is_exact():
    assert target.factorial(50) == math.factorial(50)


@pytest.mark.parametrize("n", [-1, -2, -100])
def test_factorial_negative_raises_value_error(n):
    with pytest.raises(
        ValueError, match=r"^factorial is not defined for negative numbers$"
    ):
        target.factorial(n)


@pytest.mark.parametrize(
    ("n", "fragment"),
    [
        (2.5, "cannot be interpreted as an integer"),
        (3.0, "cannot be interpreted as an integer"),
        ("5", "not supported between instances of"),
        (None, "not supported between instances of"),
        ([5], "not supported between instances of"),
    ],
    ids=lambda v: repr(v),
)
def test_factorial_wrong_type_raises_type_error(n, fragment):
    with pytest.raises(TypeError, match=fragment):
        target.factorial(n)


# --------------------------------------------------------------------------- #
# 16. average(numbers) -> float
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("numbers", "expected"),
    [
        ([5], 5.0),  # single element boundary
        ([1, 2, 3], 2.0),
        ([1, 2], 1.5),  # catches floor division
        ([1, 2, 3, 4], 2.5),
        ([-1, 1], 0.0),
        ([-2, -4], -3.0),
        ([0, 0, 0], 0.0),
        ([2.5, 3.5], 3.0),
        ((2, 4), 3.0),  # a tuple works
        ([10**6] * 1000, 1000000.0),
    ],
    ids=lambda v: repr(v)[:30],
)
def test_average_exact_results(numbers, expected):
    result = target.average(numbers)
    assert result == expected
    assert type(result) is float


@pytest.mark.parametrize(
    ("numbers", "expected"),
    [([0.1, 0.2, 0.3], 0.2), ([1, 2, 2], 5 / 3), ([0.1] * 10, 0.1)],
)
def test_average_inexact_results(numbers, expected):
    # Python 3.12 changed sum() to compensated summation, so the last bit of
    # these results differs between 3.10/3.11 and 3.12 - approx is required.
    assert target.average(numbers) == pytest.approx(expected)


def test_average_does_not_modify_input():
    numbers = [3, 1, 2]
    target.average(numbers)
    assert numbers == [3, 1, 2]


@pytest.mark.parametrize("numbers", [[], ()], ids=["list", "tuple"])
def test_average_empty_raises_value_error(numbers):
    with pytest.raises(ValueError, match=r"^list is empty$"):
        target.average(numbers)


@pytest.mark.parametrize(
    ("numbers", "fragment"),
    [
        (None, "has no len"),
        (5, "has no len"),
        ((x for x in [1, 2]), "has no len"),
        (["a", "b"], "unsupported operand type"),
        ([1, None], "unsupported operand type"),
        ("abc", "unsupported operand type"),
    ],
    ids=["None", "int", "generator", "strings", "int-None", "str"],
)
def test_average_wrong_type_raises_type_error(numbers, fragment):
    with pytest.raises(TypeError, match=fragment):
        target.average(numbers)


def test_average_overflow_characterises_current_behaviour():
    # The true mean is 1e308, but the intermediate sum overflows to inf.
    assert target.average([1e308, 1e308]) == math.inf


def test_divide_odd_numbers_returns_float():
    assert target.divide(7, 2) == 3
