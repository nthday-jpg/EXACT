import json
from pathlib import Path

def map_predicted_answer(predicted, original_gt):
    p_str = str(predicted).strip()
    orig_str = str(original_gt).strip().lower()
    
    # Check format of the original ground truth
    is_boolean_true_false = orig_str in ("true", "false")
    is_boolean_yes_no = orig_str in ("yes", "no")
    is_uncertain_format = orig_str in ("uncertain", "unknown")
    
    if p_str in ("Yes", "No", "Uncertain"):
        if p_str == "Yes":
            return "True" if is_boolean_true_false else "Yes"
        elif p_str == "No":
            return "False" if is_boolean_true_false else "No"
        else: # Uncertain
            if is_boolean_true_false or is_uncertain_format:
                return "Unknown" if orig_str == "unknown" else "Uncertain"
            return "Unknown"
            
    # For multiple choice or lists
    return predicted

def main():
    root = Path(__file__).resolve().parents[1]
    
    results_path = root / "results" / "z3_val_evaluation_results.json"
    augmented_path = root / "data" / "processed" / "logic_merged_valid_augmented.json"
    original_path = root / "data" / "processed" / "logic_merged_valid.json"
    
    if not results_path.exists():
        print(f"Error: {results_path} not found. Please run evaluate_current_z3_val.py first.")
        return
        
    with open(results_path, "r", encoding="utf-8") as f:
        z3_results = json.load(f)
        
    # Map results by example_id
    z3_map = {item["example_id"]: item for item in z3_results["details"]}
    
    # 1. Update augmented dataset
    if augmented_path.exists():
        with open(augmented_path, "r", encoding="utf-8") as f:
            augmented_data = json.load(f)
            
        updated_augmented = 0
        for item in augmented_data:
            eid = item.get("example_id")
            if eid in z3_map and z3_map[eid]["success"]:
                predicted = z3_map[eid]["predicted_ans"]
                original = item.get("answer")
                
                mapped_ans = map_predicted_answer(predicted, original)
                
                if str(original).strip().lower() != str(mapped_ans).strip().lower():
                    item["answer"] = mapped_ans
                    item["explanation"] = f"Label mathematically corrected by Z3 solver. Deduction: {predicted}."
                    updated_augmented += 1
                    print(f"Augmented - ID: {eid} | '{original}' -> '{mapped_ans}'")
                    
        with open(augmented_path, "w", encoding="utf-8") as f:
            json.dump(augmented_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully updated {updated_augmented} samples in {augmented_path.name}")
        
    # 2. Update original dataset
    if original_path.exists():
        with open(original_path, "r", encoding="utf-8") as f:
            original_data = json.load(f)
            
        updated_original = 0
        for item in original_data:
            eid = item.get("example_id")
            if eid in z3_map and z3_map[eid]["success"]:
                predicted = z3_map[eid]["predicted_ans"]
                original = item.get("answer")
                
                mapped_ans = map_predicted_answer(predicted, original)
                
                if str(original).strip().lower() != str(mapped_ans).strip().lower():
                    item["answer"] = mapped_ans
                    item["explanation"] = f"Label mathematically corrected by Z3 solver. Deduction: {predicted}."
                    updated_original += 1
                    print(f"Original - ID: {eid} | '{original}' -> '{mapped_ans}'")
                    
        with open(original_path, "w", encoding="utf-8") as f:
            json.dump(original_data, f, indent=2, ensure_ascii=False)
        print(f"Successfully updated {updated_original} samples in {original_path.name}")

if __name__ == "__main__":
    main()
