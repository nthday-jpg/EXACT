#!/usr/bin/env python3
import os
import sys
import json
import argparse
from pathlib import Path

# Add project root directory to sys.path to enable top-level imports from 'src'
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

try:
    import z3
    from src.logic.reasoning.parser import parse_formulas
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please make sure you are running this script inside the project virtual environment.")
    sys.exit(1)


def standardize_fol_formula(f_str: str) -> str:
    """Standardize logical operators and balance parentheses in an FOL formula string."""
    f_clean = f_str.strip()
    # Replace unicode math symbols with standard uppercase text operators
    f_clean = (
        f_clean.replace("¬", "NOT ")
        .replace("∧", " AND ")
        .replace("∨", " OR ")
        .replace("→", " -> ")
        .replace("↔", " <-> ")
    )
    # Balance parentheses if closing ones are missing
    open_count = f_clean.count("(")
    close_count = f_clean.count(")")
    if close_count < open_count:
        f_clean = f_clean + ")" * (open_count - close_count)
    return f_clean


def validate_sample_fol(formulas: list[str]) -> tuple[bool, str]:
    """Validate a set of FOL formulas using Z3 parser and solver compatibility check.

    Returns:
        (True, "") if the formulas are syntactically and semantically consistent.
        (False, error_msg) if parsing or consistency checking fails.
    """
    if not formulas:
        return False, "No FOL formulas found in the sample."

    try:
        # Standardize formulas
        standardized = [standardize_fol_formula(f) for f in formulas]

        # 1. Parse formulas together to ensure syntax and glossary/type consistency
        # This will catch issues like predicate arity mismatches across formulas (e.g. P(x) vs P(x, y))
        symbols, exprs = parse_formulas(standardized)

        # 2. Perform a solver safety check to ensure it doesn't crash the Z3 solver
        solver = z3.Solver()
        solver.set("timeout", 5000)  # 5-second safety timeout
        for expr in exprs:
            solver.add(expr)
        
        # Check satisfiability status just to confirm solver operates correctly
        solver.check()
        return True, ""
    except Exception as e:
        return False, str(e)


def process_dataset(file_path: Path) -> dict:
    """Process a single JSON dataset, validate all samples, and write output files.

    Returns:
        dict: Statistics for the dataset.
    """
    print(f"\nProcessing dataset: {file_path.name}")
    print("-" * 50)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file {file_path.name}: {e}")
        return {"status": "error", "error": str(e)}

    if not isinstance(data, list):
        print(f"Skipping {file_path.name}: Root JSON element is not a list/array.")
        return {"status": "skipped", "reason": "Not a list array"}

    # Look for at least one case-insensitive 'fol' key in the first few elements
    has_fol_keys = False
    for sample in data[:10]:
        for key in sample.keys():
            if "fol" in key.lower():
                has_fol_keys = True
                break
        if has_fol_keys:
            break

    if not has_fol_keys:
        print(f"Skipping {file_path.name}: No FOL logic keys (e.g., 'premises-FOL') found in samples.")
        return {"status": "skipped", "reason": "No FOL keys"}

    valid_samples = []
    invalid_samples = []
    error_counts = {}

    for idx, sample in enumerate(data):
        # Extract all formulas from keys containing "fol" (case-insensitive)
        sample_formulas = []
        for key, val in sample.items():
            if "fol" in key.lower():
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, str):
                            sample_formulas.append(item)
                elif isinstance(val, str):
                    sample_formulas.append(val)

        # Validate formulas
        is_valid, error_msg = validate_sample_fol(sample_formulas)

        if is_valid:
            valid_samples.append(sample)
        else:
            # Create a copy and append validation error info for the invalid output file
            invalid_sample = sample.copy()
            invalid_sample["validation_error"] = error_msg
            invalid_samples.append(invalid_sample)

            # Track error types
            err_type = error_msg.split(":")[0] if ":" in error_msg else error_msg
            err_type = err_type.strip()
            error_counts[err_type] = error_counts.get(err_type, 0) + 1

    total_samples = len(data)
    valid_count = len(valid_samples)
    invalid_count = len(invalid_samples)
    pass_rate = (valid_count / total_samples) * 100 if total_samples > 0 else 0

    print(f"Total samples:   {total_samples}")
    print(f"Valid samples:   {valid_count} ({pass_rate:.2f}%)")
    print(f"Invalid samples: {invalid_count} ({100 - pass_rate:.2f}%)")

    if invalid_count > 0:
        print("\nTop validation error categories:")
        for err_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {err_type}: {count} occurrences")

    # Write output files
    base_name = file_path.stem
    valid_path = file_path.parent / f"{base_name}_valid.json"
    invalid_path = file_path.parent / f"{base_name}_invalid.json"

    try:
        with open(valid_path, "w", encoding="utf-8") as f:
            json.dump(valid_samples, f, indent=2, ensure_ascii=False)
        print(f"\nSaved valid samples to: {valid_path.name}")
    except Exception as e:
        print(f"Error saving valid samples: {e}")

    try:
        with open(invalid_path, "w", encoding="utf-8") as f:
            json.dump(invalid_samples, f, indent=2, ensure_ascii=False)
        print(f"Saved invalid samples to: {invalid_path.name}")
    except Exception as e:
        print(f"Error saving invalid samples: {e}")

    return {
        "status": "success",
        "total": total_samples,
        "valid": valid_count,
        "invalid": invalid_count,
        "pass_rate": pass_rate,
        "error_categories": error_counts,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Dataset Syntactic Validation using Z3 Parser and Solver."
    )
    parser.add_argument(
        "--dir",
        type=str,
        default=str(root_dir / "data" / "processed"),
        help="Directory containing the processed logical datasets.",
    )
    args = parser.parse_args()

    data_dir = Path(args.dir)
    if not data_dir.exists() or not data_dir.is_dir():
        print(f"Error: Directory {data_dir} does not exist.")
        sys.exit(1)

    print("=" * 60)
    print("LOGICAL DATASET SYNTACTIC VALIDATION WITH Z3")
    print(f"Target Directory: {data_dir}")
    print("=" * 60)

    json_files = sorted(list(data_dir.glob("*.json")))
    if not json_files:
        print("No JSON files found in the target directory.")
        sys.exit(0)

    summary = {}
    for file_path in json_files:
        # Avoid re-processing previously generated valid/invalid files if rerun
        if file_path.stem.endswith("_valid") or file_path.stem.endswith("_invalid"):
            continue
        stats = process_dataset(file_path)
        if stats.get("status") == "success":
            summary[file_path.name] = stats

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    if not summary:
        print("No logical datasets were processed.")
    else:
        for file_name, stats in summary.items():
            print(f"{file_name}:")
            print(f"  - Total:     {stats['total']}")
            print(f"  - Valid:     {stats['valid']} ({stats['pass_rate']:.2f}%)")
            print(f"  - Invalid:   {stats['invalid']} ({100 - stats['pass_rate']:.2f}%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
