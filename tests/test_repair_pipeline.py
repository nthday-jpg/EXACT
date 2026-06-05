import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

# Remove tests/ from sys.path to prevent shadowing the global 'z3' package
for path in list(sys.path):
    if path and Path(path).resolve() == Path(__file__).resolve().parent:
        sys.path.remove(path)

from src.data import LogicalDatasetPipeline


def test_standardize_fol_formula() -> None:
    pipeline = LogicalDatasetPipeline(llm_client=MagicMock())
    
    # Check operator translation
    assert pipeline.standardize_fol_formula("\u00acP(x) \u2227 Q(x)") == "NOT P(x) AND Q(x)"
    assert pipeline.standardize_fol_formula("P(x) \u2228 Q(x)") == "P(x) OR Q(x)"
    assert pipeline.standardize_fol_formula("P(x) \u2192 Q(x)") == "P(x) -> Q(x)"
    assert pipeline.standardize_fol_formula("P(x) \u2194 Q(x)") == "P(x) <-> Q(x)"
    
    # Check parenthesis balancing
    assert pipeline.standardize_fol_formula("ForAll(x, P(x)") == "ForAll(x, P(x))"
    assert pipeline.standardize_fol_formula("ForAll(x, P(x)))") == "ForAll(x, P(x)))"


def test_validate_sample_fol() -> None:
    pipeline = LogicalDatasetPipeline(llm_client=MagicMock())
    
    # Valid FOL formulas
    valid_formulas = [
        "Student(Ha)",
        "ForAll(x, Student(x) -> Eligible(x))"
    ]
    is_valid, err = pipeline.validate_sample_fol(valid_formulas)
    assert is_valid is True
    assert err == ""
    
    # Invalid FOL formulas (uninterpreted constant where predicate expected)
    invalid_formulas = [
        "Ha"
    ]
    is_valid, err = pipeline.validate_sample_fol(invalid_formulas)
    assert is_valid is False
    assert err != ""


def test_validate_dataset() -> None:
    pipeline = LogicalDatasetPipeline(llm_client=MagicMock())
    
    dataset = [
        {
            "example_id": "1",
            "premises-NL": ["Ha is a student.", "All students are eligible."],
            "premises-FOL": ["Student(Ha)", "ForAll(x, Student(x) -> Eligible(x))"]
        },
        {
            "example_id": "2",
            "premises-NL": ["Ha is here."],
            "premises-FOL": ["Ha"]
        }
    ]
    
    valid, invalid = pipeline.validate_dataset(dataset)
    assert len(valid) == 1
    assert len(invalid) == 1
    assert valid[0]["example_id"] == "1"
    assert invalid[0]["example_id"] == "2"
    assert "validation_error" in invalid[0]


def test_repair_sample_success() -> None:
    mock_client = MagicMock()
    # Mock LLM returning valid repaired json string
    mock_client.generate_text.return_value = """
    ```json
    {
      "example_id": "2",
      "premises-NL": ["All students are eligible."],
      "premises-FOL": ["ForAll(x, Student(x) -> Eligible(x))"]
    }
    ```
    """
    
    pipeline = LogicalDatasetPipeline(llm_client=mock_client)
    
    sample = {
        "example_id": "2",
        "premises-NL": ["All students are eligible."],
        "premises-FOL": ["Ha"]
    }
    
    success, repaired = pipeline.repair_sample(sample)
    assert success is True
    assert repaired["premises-FOL"] == ["ForAll(x, Student(x) -> Eligible(x))"]
    assert "validation_error" not in repaired


def test_repair_sample_failure() -> None:
    mock_client = MagicMock()
    # Mock LLM returning invalid response
    mock_client.generate_text.return_value = "invalid response"
    
    pipeline = LogicalDatasetPipeline(llm_client=mock_client)
    
    sample = {
        "example_id": "3",
        "premises-NL": ["All students are eligible."],
        "premises-FOL": ["Ha"]
    }
    
    success, repaired = pipeline.repair_sample(sample, max_retries=1)
    assert success is False
    assert "validation_error" in repaired
    assert "Failed to repair" in repaired["validation_error"]


def main() -> None:
    print("=" * 80)
    print("RUNNING LOGICAL REPAIR PIPELINE TESTS")
    print("=" * 80)
    
    print("Running test_standardize_fol_formula...")
    test_standardize_fol_formula()
    print("  [PASSED]")
    
    print("Running test_validate_sample_fol...")
    test_validate_sample_fol()
    print("  [PASSED]")
    
    print("Running test_validate_dataset...")
    test_validate_dataset()
    print("  [PASSED]")
    
    print("Running test_repair_sample_success...")
    test_repair_sample_success()
    print("  [PASSED]")
    
    print("Running test_repair_sample_failure...")
    test_repair_sample_failure()
    print("  [PASSED]")
    
    print("\n" + "=" * 80)
    print("ALL REPAIR PIPELINE TESTS PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    main()
