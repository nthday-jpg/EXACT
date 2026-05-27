import pytest

from src.physics.postprocessing import postprocess_answer


def test_postprocess_single_value_to_prefix():
    payload = {"ans": "1e-3", "unit": "m"}
    result = postprocess_answer(payload)
    assert result["ans"] == "1"
    assert result["unit"] == "mm"


def test_postprocess_squared_unit_to_prefix():
    payload = {"ans": "1e-6", "unit": "m^2"}
    result = postprocess_answer(payload)
    assert result["ans"] == "1"
    assert result["unit"] == "mm^2"


def test_postprocess_micro_prefix():
    payload = {"ans": "1e-6", "unit": "m"}
    result = postprocess_answer(payload)
    assert result["ans"] == "1"
    assert result["unit"] == "μm"


def test_postprocess_keeps_prefixed_units():
    payload = {"ans": "1e-3", "unit": "mm"}
    result = postprocess_answer(payload)
    assert result == payload


def test_postprocess_keeps_non_divisible_exponent():
    payload = {"ans": "1e-5", "unit": "m^2"}
    result = postprocess_answer(payload)
    assert result == payload


def test_postprocess_list_values_with_units():
    payload = {"ans": ["1e-3", "2e3"], "unit": ["m", "s"]}
    result = postprocess_answer(payload)
    assert result["ans"] == ["1", "2"]
    assert result["unit"] == ["mm", "ks"]
