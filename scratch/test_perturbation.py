import json
import sys
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.data.augmentation.entity_anonymizer import EntityAnonymizer

def main():
    merged_path = root_dir / "data" / "processed" / "logic_merged_valid.json"
    if not merged_path.exists():
        print(f"Error: logic_merged_valid.json not found at {merged_path}")
        return

    with open(merged_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Instantiate anonymizer
    anonymizer = EntityAnonymizer()

    # Try on a few samples
    count = 0
    for idx, sample in enumerate(data):
        if count >= 3:
            break
        
        nl = sample.get("premises-NL", [])
        fol = sample.get("premises-FOL", [])
        
        # Apply perturbation strategy
        perturbed = anonymizer.anonymize_sample(sample, strategy="perturbation", variant_idx=0)
        if perturbed:
            print(f"\n=== Original Sample {idx} ===")
            print(f"NL: {nl}")
            print(f"FOL: {fol}")
            print(f"--- Perturbed Sample ---")
            print(f"NL: {perturbed['premises-NL']}")
            print(f"FOL: {perturbed['premises-FOL']}")
            count += 1

if __name__ == "__main__":
    main()
