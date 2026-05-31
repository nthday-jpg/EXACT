import sys
import json
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from scripts.validate_dataset_syntax import validate_sample_fol

def main():
    print("=" * 80)
    print("Z3 SYNTAX VALIDATION FOR AUGMENTED SAMPLES")
    print("=" * 80)
    
    merged_path = root_dir / "data" / "processed" / "merged_valid.json"
    
    with open(merged_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    augmented_samples = [s for s in data if "augmented" in s.get("dataset_source", "")]
    print(f"Loaded {len(augmented_samples)} augmented samples for Z3 validation...")
    
    passed_count = 0
    failed_count = 0
    failures = []
    
    for idx, sample in enumerate(augmented_samples):
        # Gather all FOL formulas
        fol_formulas = list(sample.get("premises-FOL", []))
        
        is_valid, error_msg = validate_sample_fol(fol_formulas)
        if is_valid:
            passed_count += 1
        else:
            failed_count += 1
            failures.append({
                "example_id": sample.get("example_id"),
                "formulas": fol_formulas,
                "error": error_msg
            })
            
    print(f"Z3 Validation Results:")
    print(f"  - Passed: {passed_count} ({passed_count / len(augmented_samples) * 100:.2f}%)")
    print(f"  - Failed: {failed_count} ({failed_count / len(augmented_samples) * 100:.2f}%)")
    
    if failures:
        print("\n" + "!" * 40)
        print("FIRST 5 Z3 SYNTAX FAILURES IN AUGMENTED DATA:")
        print("!" * 40)
        for f in failures[:5]:
            print(f"\nSample ID: {f['example_id']}")
            print(f"Formulas: {f['formulas']}")
            print(f"Error: {f['error']}")
    else:
        print("\n[SUCCESS] 100% of newly augmented FOL formulas are completely valid in Z3 parser and solver!")
    print("=" * 80)

if __name__ == "__main__":
    main()
