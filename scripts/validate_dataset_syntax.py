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
    f_clean = (
        f_clean.replace("¬", "NOT ")
        .replace("∧", " AND ")
        .replace("∨", " OR ")
        .replace("→", " -> ")
        .replace("↔", " <-> ")
    )
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
        symbols, exprs = parse_formulas(standardized)

        # 2. Perform a solver safety check to ensure it doesn't crash the Z3 solver
        solver = z3.Solver()
        solver.set("timeout", 5000)  # 5-second safety timeout
        for expr in exprs:
            solver.add(expr)
        
        solver.check()
        return True, ""
    except Exception as e:
        return False, str(e)


def unify_sample(sample: dict, dataset_name: str, parent_idx: int) -> list[dict]:
    """Convert sample from a specific dataset into the unified schema.
    Since some datasets (like logic_based) store multiple questions per set of premises,
    this returns a list of unified samples (one for each question).
    """
    unified_samples = []

    # Identify all FOL formulas for validation
    sample_formulas = []
    for key, val in sample.items():
        if "fol" in key.lower():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        sample_formulas.append(item)
            elif isinstance(val, str):
                sample_formulas.append(val)

    # Run validation
    is_valid, error_msg = validate_sample_fol(sample_formulas)

    if dataset_name == "folio-train":
        # folio-train contains a single question/conclusion per sample
        unified = {
            "dataset_source": "folio-train",
            "story_id": sample.get("story_id"),
            "example_id": str(sample.get("example_id", parent_idx)),
            "premises-NL": sample.get("premises-NL", []),
            "premises-FOL": sample.get("premises-FOL", []),
            "question": sample.get("conclusion", ""),
            "answer": sample.get("label", ""),
            "explanation": None,
        }
        if not is_valid:
            unified["validation_error"] = error_msg
        unified_samples.append((is_valid, unified))

    elif dataset_name == "logic_based":
        # logic_based contains multiple questions, answers, and explanations per sample
        questions = sample.get("questions", [])
        answers = sample.get("answers", [])
        explanations = sample.get("explanation", [])  # logic_based uses singular 'explanation' as list

        num_questions = len(questions)
        for i in range(num_questions):
            q_text = questions[i] if i < len(questions) else ""
            a_text = answers[i] if i < len(answers) else ""
            e_text = explanations[i] if i < len(explanations) else None

            unified = {
                "dataset_source": "logic_based",
                "story_id": str(parent_idx),
                "example_id": f"{parent_idx}_{i}",
                "premises-NL": sample.get("premises-NL", []),
                "premises-FOL": sample.get("premises-FOL", []),
                "question": q_text,
                "answer": a_text,
                "explanation": e_text,
            }
            if not is_valid:
                unified["validation_error"] = error_msg
            unified_samples.append((is_valid, unified))
            
    else:
        # Generic fallback format
        unified = {
            "dataset_source": dataset_name,
            "story_id": str(sample.get("story_id", parent_idx)),
            "example_id": str(sample.get("example_id", parent_idx)),
            "premises-NL": sample.get("premises-NL", []),
            "premises-FOL": sample.get("premises-FOL", []),
            "question": sample.get("question", sample.get("conclusion", "")),
            "answer": sample.get("answer", sample.get("label", "")),
            "explanation": sample.get("explanation"),
        }
        if not is_valid:
            unified["validation_error"] = error_msg
        unified_samples.append((is_valid, unified))

    return unified_samples


def main():
    parser = argparse.ArgumentParser(
        description="Dataset Syntactic Validation and Format Unification."
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

    print("=" * 70)
    print("LOGICAL DATASET SYNTACTIC VALIDATION & UNIFICATION WITH Z3")
    print(f"Target Directory: {data_dir}")
    print("=" * 70)

    json_files = sorted(list(data_dir.glob("*.json")))
    if not json_files:
        print("No JSON files found in the target directory.")
        sys.exit(0)

    all_valid_samples = []
    all_invalid_samples = []
    
    summary = {}

    for file_path in json_files:
        # Skip output files from previous runs
        if file_path.stem.endswith("_valid") or file_path.stem.endswith("_invalid") or file_path.stem.startswith("merged_"):
            continue

        print(f"\nProcessing: {file_path.name}")
        print("-" * 50)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading JSON file {file_path.name}: {e}")
            continue

        if not isinstance(data, list):
            print(f"Skipping {file_path.name}: Root is not a list array.")
            continue

        # Look for at least one case-insensitive 'fol' key to identify logic datasets
        has_fol_keys = False
        for sample in data[:10]:
            for key in sample.keys():
                if "fol" in key.lower():
                    has_fol_keys = True
                    break
            if has_fol_keys:
                break

        if not has_fol_keys:
            print(f"Skipping {file_path.name}: No FOL logic keys found.")
            continue

        dataset_name = file_path.stem
        valid_count = 0
        invalid_count = 0
        total_questions = 0

        for idx, sample in enumerate(data):
            unified_results = unify_sample(sample, dataset_name, idx)
            for is_valid, unified in unified_results:
                total_questions += 1
                if is_valid:
                    all_valid_samples.append(unified)
                    valid_count += 1
                else:
                    all_invalid_samples.append(unified)
                    invalid_count += 1

        pass_rate = (valid_count / total_questions) * 100 if total_questions > 0 else 0
        print(f"Processed questions: {total_questions}")
        print(f"Valid questions:     {valid_count} ({pass_rate:.2f}%)")
        print(f"Invalid questions:   {invalid_count} ({100 - pass_rate:.2f}%)")

        summary[file_path.name] = {
            "total": total_questions,
            "valid": valid_count,
            "invalid": invalid_count,
            "pass_rate": pass_rate
        }

    # Save the merged outputs
    merged_valid_path = data_dir / "merged_valid.json"
    merged_invalid_path = data_dir / "merged_invalid.json"

    print("\n" + "=" * 70)
    print("SAVING MERGED DATASETS (UNIFIED FORMAT)")
    print("=" * 70)

    try:
        with open(merged_valid_path, "w", encoding="utf-8") as f:
            json.dump(all_valid_samples, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(all_valid_samples)} unified valid samples to:")
        print(f"  -> {merged_valid_path}")
    except Exception as e:
        print(f"Error saving merged valid file: {e}")

    try:
        with open(merged_invalid_path, "w", encoding="utf-8") as f:
            json.dump(all_invalid_samples, f, indent=2, ensure_ascii=False)
        print(f"Successfully saved {len(all_invalid_samples)} unified invalid samples to:")
        print(f"  -> {merged_invalid_path}")
    except Exception as e:
        print(f"Error saving merged invalid file: {e}")

    print("\n" + "=" * 70)
    print("FINAL SUMMARY REPORT")
    print("=" * 70)
    for file_name, stats in summary.items():
        print(f"{file_name}:")
        print(f"  - Total unified questions: {stats['total']}")
        print(f"  - Valid questions:         {stats['valid']} ({stats['pass_rate']:.2f}%)")
        print(f"  - Invalid questions:       {stats['invalid']} ({100 - stats['pass_rate']:.2f}%)")
    print("-" * 70)
    print(f"Grand Total Valid:   {len(all_valid_samples)}")
    print(f"Grand Total Invalid: {len(all_invalid_samples)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
