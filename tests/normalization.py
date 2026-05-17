from utils.normalization import (
    extract_value_unit_explanation,
    normalize_physics_input,
    normalize_physics_output,
)


def test_normalize_input_symbols() -> None:
    text = "q = 6 \u00d7 10\u207b\u2078 C and q2 = -6 \u00b7 10\u207b\u2078 C"
    expected = "q = 6 * 10^-8 C and q2 = -6 * 10^-8 C"
    assert normalize_physics_input(text) == expected


def test_normalize_input_minus_and_fraction() -> None:
    text = "distance \u2212 1/2 m\u00a0and 1\u20443 m"
    expected = "distance - 1/2 m and 1/3 m"
    assert normalize_physics_input(text) == expected


def test_normalize_output_units_and_spacing() -> None:
    text = "F = m \u00d7 a = 2 \u00d7 10\u207b\u00b3 \u03a9"
    expected = "F=m*a=2*10^-3 ohm"
    assert normalize_physics_output(text) == expected


def test_normalize_output_fractions_decimal() -> None:
    text = "1/2 + 1\u20442"
    expected = "0.5+0.5"
    assert normalize_physics_output(text) == expected


def test_extract_value_unit_explanation() -> None:
    text = "9.8 m/s^2 because gravity"
    result = extract_value_unit_explanation(text)
    assert result["value"] == 9.8
    assert result["unit"] == "m/s^2"
    assert result["explanation"] == "because gravity"


def test_normalize_input_sample_x_notation() -> None:
    text = "Pressure increases by 2 x 10\u2075 Pa and 5 x 10\u2075 Pa."
    expected = "Pressure increases by 2 x 10^5 Pa and 5 x 10^5 Pa."
    assert normalize_physics_input(text) == expected


def test_normalize_output_sample_superscripts() -> None:
    text = "|Q| = 4 x 10\u207b\u2078 C at r = 5 cm"
    expected = "|Q|=4 x 10^-8 C at r=5 cm"
    assert normalize_physics_output(text) == expected


if __name__ == "__main__":
    test_normalize_input_symbols()
    test_normalize_input_minus_and_fraction()
    test_normalize_output_units_and_spacing()
    test_normalize_output_fractions_decimal()
    test_extract_value_unit_explanation()
    test_normalize_input_sample_x_notation()
    test_normalize_output_sample_superscripts()
    print("All normalization tests passed.")
