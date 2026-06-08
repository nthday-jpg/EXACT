import json
import sys
import re
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.utils.normalization import normalize_logic_fol_entry

def process_dataset(filepath):
    print(f"Processing {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    num_changed_formulas = 0
    num_changed_samples = 0
    
    for item in data:
        fol_list = item.get("premises-FOL")
        if fol_list:
            new_fol_list = []
            changed_in_sample = False
            for fol in fol_list:
                normalized = normalize_logic_fol_entry(fol)
                if normalized != fol:
                    num_changed_formulas += 1
                    changed_in_sample = True
                new_fol_list.append(normalized)
            item["premises-FOL"] = new_fol_list
            if changed_in_sample:
                num_changed_samples += 1
                
    print(f"Changed {num_changed_formulas} formulas across {num_changed_samples}/{len(data)} samples.")
    
    # Save back
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Saved successfully.")

if __name__ == "__main__":
    process_dataset(root / "data" / "processed" / "logic_merged_valid.json")
    process_dataset(root / "data" / "processed" / "logic_merged_valid_augmented.json")
