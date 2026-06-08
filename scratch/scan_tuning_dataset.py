import json
import sys
from pathlib import Path
import z3

# Add project root directory to sys.path to enable top-level imports from 'src'
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.logic.reasoning.verifier import parse_formulas
from src.data.cleaning.formatter import standardize_fol_formula

def validate_single_sample(sample: dict) -> tuple[bool, str]:
    nl = sample.get("premises-NL", [])
    fol = sample.get("premises-FOL", [])
    
    # 1. Check if empty
    if not nl and not fol:
        return False, "Empty premises-NL and premises-FOL lists."
    if not fol:
        return False, "Empty premises-FOL list."
    if not nl:
        return False, "Empty premises-NL list."
        
    # 2. Check length mismatch
    if len(nl) != len(fol):
        return False, f"Premise count mismatch: premises-NL has {len(nl)} elements, but premises-FOL has {len(fol)} elements."
        
    # 3. Check for forbidden characters in FOL formulas
    forbidden = []
    for f in fol:
        if "/" in f:
            forbidden.append(f"Contains division '/': {f}")
        if "*" in f:
            forbidden.append(f"Contains multiplication '*': {f}")
        if "[" in f or "]" in f:
            forbidden.append(f"Contains brackets []: {f}")
    if forbidden:
        return False, f"Forbidden characters found: {'; '.join(forbidden)}"
        
    # 4. Attempt Z3 parsing and solver check
    try:
        standardized = [standardize_fol_formula(f) for f in fol]
        symbols, exprs = parse_formulas(standardized)
        
        solver = z3.Solver()
        solver.set("timeout", 5000)  # 5-second safety timeout
        for expr in exprs:
            solver.add(expr)
        
        # Check if premises are contradictory
        if solver.check() == z3.unsat:
            return False, "Contradictory premises: The premises themselves are unsatisfiable (UNSAT)."
            
        return True, ""
    except Exception as e:
        return False, f"Z3 Parse/Solver Error: {str(e)}"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scan a logical reasoning dataset for Z3 and syntax issues.")
    parser.add_argument(
        "--input", "-i",
        default=str(root_dir / "data" / "processed" / "logic_merged_valid_augmented.json"),
        help="Path to the input JSON dataset file"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(root_dir / "scratch" / "problematic_tuning_samples.json"),
        help="Path to save the problematic JSON samples to"
    )
    args = parser.parse_args()
    
    dataset_path = Path(args.input)
    output_path = Path(args.output)
    
    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        sys.exit(1)
        
    print(f"Scanning dataset: {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Total samples loaded: {len(data)}")
    
    problematic_samples = []
    failure_types = {
        "empty_premises": 0,
        "mismatched_length": 0,
        "forbidden_chars": 0,
        "z3_error": 0,
        "contradictory_premises": 0
    }
    
    passed_count = 0
    for idx, sample in enumerate(data):
        is_valid, err_msg = validate_single_sample(sample)
        if is_valid:
            passed_count += 1
        else:
            problematic = sample.copy()
            problematic["scan_index"] = idx
            problematic["validation_error"] = err_msg
            problematic_samples.append(problematic)
            
            # Classify error
            if "Empty" in err_msg:
                failure_types["empty_premises"] += 1
            elif "Premise count mismatch" in err_msg:
                failure_types["mismatched_length"] += 1
            elif "Forbidden characters" in err_msg:
                failure_types["forbidden_chars"] += 1
            elif "Contradictory premises" in err_msg:
                failure_types["contradictory_premises"] += 1
            elif "Z3" in err_msg:
                failure_types["z3_error"] += 1
                
    print("\n" + "=" * 80)
    print("SCANNING RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total Scanned:     {len(data)}")
    print(f"Passed Valid:      {passed_count} ({passed_count / len(data) * 100:.2f}%)")
    print(f"Failed/Problematic: {len(problematic_samples)} ({len(problematic_samples) / len(data) * 100:.2f}%)")
    print("-" * 80)
    print("Failure Breakdown:")
    for f_type, count in failure_types.items():
        print(f"  - {f_type:20s}: {count}")
    print("=" * 80)
    
    # Save output file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(problematic_samples, f, indent=2, ensure_ascii=False)
    print(f"\nProblematic samples successfully saved to: {output_path}")

if __name__ == "__main__":
    main()
