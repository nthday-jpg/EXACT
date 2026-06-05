import json
import random

merged_path = r"d:\mduy\source\repos\EXACT\data\processed\merged_valid.json"

with open(merged_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("AUGMENTED DATASET VERIFICATION")
print("=" * 80)
print(f"Total samples: {len(data)}")

original_count = 0
letters_count = 0
names_count = 0
other_aug_count = 0

mismatch_samples = []

for idx, sample in enumerate(data):
    source = sample.get("dataset_source", "")
    if "augmented-letters" in source:
        letters_count += 1
    elif "augmented-names" in source:
        names_count += 1
    elif "augmented" in source:
        other_aug_count += 1
    else:
        original_count += 1
        
    nl_len = len(sample.get("premises-NL", []))
    fol_len = len(sample.get("premises-FOL", []))
    if nl_len != fol_len:
        mismatch_samples.append((idx, sample.get("example_id"), nl_len, fol_len))

print(f"Original samples: {original_count}")
print(f"Augmented (Letters) samples: {letters_count}")
print(f"Augmented (Names) samples: {names_count}")
print(f"Other Augmented samples: {other_aug_count}")
print(f"Total Augmented samples: {letters_count + names_count + other_aug_count}")

print(f"\nPremise count alignment checks:")
if not mismatch_samples:
    print("  [OK] 100% of samples have perfectly aligned NL and FOL premise lengths!")
else:
    print(f"  [WARNING] Found {len(mismatch_samples)} samples with mismatched premise counts!")
    for idx, eid, nl_l, fol_l in mismatch_samples[:5]:
        print(f"    - Sample index {idx} (ID: {eid}): NL={nl_l}, FOL={fol_l}")

# Randomly sample 3 augmented samples and print them
print("\n" + "-" * 40)
print("RANDOM AUGMENTED SAMPLES DEMO")
print("-" * 40)
augmented_indices = [i for i, s in enumerate(data) if "augmented" in s.get("dataset_source", "")]
if augmented_indices:
    sampled_indices = random.sample(augmented_indices, min(3, len(augmented_indices)))
    for idx in sampled_indices:
        sample = data[idx]
        print(f"\nSample Index {idx} (ID: {sample.get('example_id')})")
        print(f"Dataset Source: {sample.get('dataset_source')}")
        print("NL Premises:")
        for nl in sample.get("premises-NL", []):
            print(f"  - {nl}")
        print("FOL Premises:")
        for fol in sample.get("premises-FOL", []):
            print(f"  - {fol}")
        print(f"Question: {sample.get('question')}")
        print(f"Answer: {sample.get('answer')}")
else:
    print("No augmented samples found in the dataset to demo.")
print("=" * 80)
