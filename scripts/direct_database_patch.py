#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

# Add project root directory to sys.path to enable top-level imports from 'src'
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

try:
    from scripts.validate_dataset_syntax import validate_sample_fol
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)


# Exact qualitative, Z3-valid FOL translations for the remaining 2 invalid samples
REPAIRED_FOLs = {
    # 65% total credits (379)
    "379_0": [
        "ForAll(s, (EligibleForInternship(s) <-> AccumulatedCredits(s) >= 78))",
        "TotalCredits(TrainingProgram) = 120",
        "AccumulatedCredits(Ha) = 80",
        "ForAll(s, (EligibleForInternship(s) -> SubmittedApplicationBeforeJune1(s)))",
        "SubmittedApplicationBeforeJune1(Ha)",
        "ElectiveCredits(TrainingProgram) = 30",
        "CountedElectiveCredits(TrainingProgram) = 20",
        "AccumulatedCredits(Vinh) = 75",
        "Program(Vinh, TrainingProgram)",
        "ForAll(s, (GPA(s) < 2.5 -> RequiresRemedialCourse(s)))",
        "GPA(Ha) = 3.2",
        "NOT RequiresRemedialCourse(Ha)",
        "InternshipCycle(Summer) AND InternshipCycle(Fall)",
        "Priority(Summer, Seniors)",
        "Status(Ha, Junior) AND ApplyingFor(Ha, Fall)",
        "ForAll(s, (EligibleForInternship(s) -> ApprovedByAdvisor(s)))",
        "ApprovedByAdvisor(Ha)",
        "NOT SubmittedApplicationBeforeJune1(Vinh)",
        "ElectiveCreditsAccumulated(Vinh) = 10"
    ],
    "379_1": [
        "ForAll(s, (EligibleForInternship(s) <-> AccumulatedCredits(s) >= 78))",
        "TotalCredits(TrainingProgram) = 120",
        "AccumulatedCredits(Ha) = 80",
        "ForAll(s, (EligibleForInternship(s) -> SubmittedApplicationBeforeJune1(s)))",
        "SubmittedApplicationBeforeJune1(Ha)",
        "ElectiveCredits(TrainingProgram) = 30",
        "CountedElectiveCredits(TrainingProgram) = 20",
        "AccumulatedCredits(Vinh) = 75",
        "Program(Vinh, TrainingProgram)",
        "ForAll(s, (GPA(s) < 2.5 -> RequiresRemedialCourse(s)))",
        "GPA(Ha) = 3.2",
        "NOT RequiresRemedialCourse(Ha)",
        "InternshipCycle(Summer) AND InternshipCycle(Fall)",
        "Priority(Summer, Seniors)",
        "Status(Ha, Junior) AND ApplyingFor(Ha, Fall)",
        "ForAll(s, (EligibleForInternship(s) -> ApprovedByAdvisor(s)))",
        "ApprovedByAdvisor(Ha)",
        "NOT SubmittedApplicationBeforeJune1(Vinh)",
        "ElectiveCreditsAccumulated(Vinh) = 10"
    ]
}


def main():
    print("=" * 80)
    print("DIRECT PATCHING AND RESOLUTION FOR FINAL 2 COMPLEX SAMPLES")
    print("Applies hand-crafted, logically robust uninterpreted logic translations.")
    print("=" * 80)

    data_dir = root_dir / "data" / "processed"
    invalid_path = data_dir / "merged_invalid.json"
    valid_path = data_dir / "merged_valid.json"

    if not invalid_path.exists():
        print(f"Error: {invalid_path} does not exist.")
        sys.exit(1)

    # Load invalid samples
    with open(invalid_path, "r", encoding="utf-8") as f:
        invalid_samples = json.load(f)

    if not invalid_samples:
        print("No invalid samples to patch!")
        sys.exit(0)

    print(f"Loaded {len(invalid_samples)} invalid samples from merged_invalid.json.")

    with open(valid_path, "r", encoding="utf-8") as f:
        valid_samples = json.load(f)

    patched_count = 0
    remaining_invalid = []

    for sample in invalid_samples:
        ex_id = sample["example_id"]
        if ex_id in REPAIRED_FOLs:
            print(f"Patching Sample {ex_id}...")
            
            # Apply repaired FOLs
            repaired_fol = REPAIRED_FOLs[ex_id]
            sample["premises-FOL"] = repaired_fol
            sample.pop("validation_error", None)

            # Validate
            is_valid, error_msg = validate_sample_fol(repaired_fol)
            if is_valid:
                print(f"  [SUCCESS] Sample {ex_id} verified successfully by Z3 parser!")
                valid_samples.append(sample)
                patched_count += 1
            else:
                print(f"  [FAILED] Sample {ex_id} validation failed: {error_msg}")
                sample["validation_error"] = error_msg
                remaining_invalid.append(sample)
        else:
            remaining_invalid.append(sample)

    # Save files
    with open(valid_path, "w", encoding="utf-8") as f:
        json.dump(valid_samples, f, indent=2, ensure_ascii=False)
    with open(invalid_path, "w", encoding="utf-8") as f:
        json.dump(remaining_invalid, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("PATCHING COMPLETED")
    print("=" * 80)
    print(f"Total successfully patched and merged: {patched_count}")
    print(f"Total remaining invalid:                {len(remaining_invalid)}")
    print(f"Total valid in dataset:                 {len(valid_samples)}")
    print("=" * 80)


if __name__ == "__main__":
    main()
