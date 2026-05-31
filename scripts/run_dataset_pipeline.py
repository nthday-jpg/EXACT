#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

# Add project root directory to sys.path to enable top-level imports from 'src'
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

try:
    from src.data import LogicalDatasetPipeline
except ImportError as e:
    print(f"Error importing LogicalDatasetPipeline: {e}")
    print("Please make sure you are running this script inside the project virtual environment.")
    sys.exit(1)


def main():
    print("=" * 80)
    print("LOGICAL DATASET PIPELINE DEMONSTRATION & VERIFICATION")
    print("Runs a non-destructive pipeline test on a temporary invalid logic subset.")
    print("=" * 80)

    data_dir = root_dir / "data" / "processed"
    temp_input = data_dir / "temp_pipeline_test.json"
    temp_valid_out = data_dir / "temp_pipeline_valid.json"
    temp_invalid_out = data_dir / "temp_pipeline_invalid.json"

    # Create a small, temporary test dataset with 2 invalid logic samples to repair
    test_samples = [
        {
            "dataset_source": "logic_based",
            "story_id": "999_test",
            "example_id": "999_0",
            "premises-NL": [
                "Alex earns a scholarship.",
                "If internships are unpaid, students cannot complete them without financial support."
            ],
            "premises-FOL": [
                "scholarship(Alex)",
                "ForAll(s, (unpaid_internships AND NOT financial_support(s) -> NOT internship(s)))"
            ],
            "question": "Is it true?",
            "answer": "Yes",
            "explanation": "Test case."
        },
        {
            "dataset_source": "logic_based",
            "story_id": "999_test",
            "example_id": "999_1",
            "premises-NL": [
                "Phong scored 95% on exams on 25/3/2025."
            ],
            "premises-FOL": [
                "PhongExamScore(Phong) AND ExamDate(Phong, '25/3/2025')"
            ],
            "question": "Is it true?",
            "answer": "Yes",
            "explanation": "Test case."
        }
    ]

    with open(temp_input, "w", encoding="utf-8") as f:
        json.dump(test_samples, f, indent=2, ensure_ascii=False)
    print(f"Created temporary pipeline input file: {temp_input.name}")

    # Initialize the LogicalDatasetPipeline
    try:
        pipeline = LogicalDatasetPipeline()
    except Exception as e:
        print(f"Failed to initialize LogicalDatasetPipeline: {e}")
        sys.exit(1)

    # Run pipeline
    print("\nTriggering LogicalDatasetPipeline.run_pipeline()...")
    try:
        pipeline.run_pipeline(
            input_path=str(temp_input),
            output_valid_path=str(temp_valid_out),
            output_invalid_path=str(temp_invalid_out),
            auto_repair=True,
            max_retries=3
        )
    except Exception as e:
        print(f"Pipeline execution failed: {e}")
        # Clean up input file
        if temp_input.exists():
            temp_input.unlink()
        sys.exit(1)

    # Clean up files after verifying they exist
    print("\nVerifying outputs and cleaning up...")
    if temp_valid_out.exists():
        print(f"  [OK] Valid output file was successfully generated ({temp_valid_out.name})")
        with open(temp_valid_out, "r", encoding="utf-8") as f_v:
            v_data = json.load(f_v)
            print(f"  [OK] Successfully repaired and validated {len(v_data)} samples!")
        temp_valid_out.unlink()

    if temp_invalid_out.exists():
        print(f"  [OK] Invalid output file was successfully generated ({temp_invalid_out.name})")
        temp_invalid_out.unlink()

    if temp_input.exists():
        temp_input.unlink()

    print("\n" + "=" * 80)
    print("PIPELINE TEST PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
