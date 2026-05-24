from src.eval.eval_physics import evaluate_physics_answer


def test_unit_dash_and_empty_equal() -> None:
	model = {"ans": 1, "unit": ""}
	correct = {"ans": 1, "unit": "-"}
	assert evaluate_physics_answer(model, correct)


def test_unit_equivalence_v_per_m_and_n_per_c() -> None:
	model = {"ans": ["4.3142e5"], "unit": ["N/C"]}
	correct = {"ans": "432000", "unit": "V/m"}
	assert evaluate_physics_answer(model, correct)


def test_list_swapped_with_units() -> None:
	model = {"ans": [0.2, 0.1], "unit": ["C", "N"]}
	correct = {"ans": [0.1, 0.2], "unit": ["N", "C"]}
	assert evaluate_physics_answer(model, correct)


def test_formula_equivalence() -> None:
	model = {"ans": "x + 1", "unit": "-"}
	correct = {"ans": "1 + x", "unit": ""}
	assert evaluate_physics_answer(model, correct)


if __name__ == "__main__":
	test_unit_dash_and_empty_equal()
	test_unit_equivalence_v_per_m_and_n_per_c()
	test_list_swapped_with_units()
	test_formula_equivalence()
	print("All eval_physics tests passed.")
