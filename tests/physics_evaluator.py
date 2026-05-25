from src.physics.evaluator import PhysicsEvaluator
from src.physics.types import PhysicsResult, PhysicsTask


def _make_result(*, model_answer=None, correct=None, error=None):
    task = PhysicsTask(question="q", correct=correct)
    return PhysicsResult(
        task=task,
        model_answer=model_answer,
        raw_response="",
        error=error,
        tokens=None,
        elapsed_s=0.0,
    )


def test_missing_correct() -> None:
    evaluator = PhysicsEvaluator()
    result = _make_result(model_answer={"ans": 1, "unit": "N"}, correct=None)
    eval_result = evaluator.evaluate(result)
    assert eval_result.is_correct is None
    assert eval_result.reason == "missing_correct"


def test_missing_answer_json_error() -> None:
    evaluator = PhysicsEvaluator()
    result = _make_result(model_answer=None, correct={"ans": 1, "unit": "N"}, error="JSON decode error")
    eval_result = evaluator.evaluate(result)
    assert eval_result.is_correct is False
    assert eval_result.reason == "json_parse_error"


def test_missing_answer_syntax_error() -> None:
    evaluator = PhysicsEvaluator()
    result = _make_result(model_answer=None, correct={"ans": 1, "unit": "N"}, error="SyntaxError: invalid syntax")
    eval_result = evaluator.evaluate(result)
    assert eval_result.is_correct is False
    assert eval_result.reason == "code_syntax_error"


def test_nan_answer() -> None:
    evaluator = PhysicsEvaluator()
    result = _make_result(model_answer={"ans": ["nan"], "unit": [""]}, correct={"ans": 1, "unit": ""})
    eval_result = evaluator.evaluate(result)
    assert eval_result.is_correct is False
    assert eval_result.reason == "nan_answer"


if __name__ == "__main__":
    test_missing_correct()
    test_missing_answer_json_error()
    test_missing_answer_syntax_error()
    test_nan_answer()
    print("All physics evaluator tests passed.")
