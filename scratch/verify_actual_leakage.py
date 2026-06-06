import json
from collections import Counter, defaultdict

augmented_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json"

with open(augmented_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total samples: {len(data)}")

# Group by split
split_counts = Counter(s.get("split", "unknown") for s in data)
print("\n=== Split Distribution ===")
for split, count in split_counts.items():
    print(f"  - {split}: {count}")

train_samples = [s for s in data if s.get("split") == "train"]
val_samples = [s for s in data if s.get("split") == "val"]

# 1. Verify that validation set has NO augmented samples
val_sources = Counter(s.get("dataset_source", "unknown") for s in val_samples)
print("\n=== Validation Sources ===")
for src, count in val_sources.items():
    print(f"  - {src}: {count}")

# 2. Check for data leakage by comparing story/original IDs
train_original_ids = set()
for s in train_samples:
    eid = s.get("example_id", "")
    orig_id = eid
    if "_perm_var" in eid:
        orig_id = eid.split("_perm_var")[0]
    elif "_aug_var" in eid:
        orig_id = eid.split("_aug_var")[0]
    elif "_neg_var" in eid:
        orig_id = eid.split("_neg_var")[0]
    train_original_ids.add(orig_id)

val_leakages = 0
for s in val_samples:
    eid = s.get("example_id", "")
    orig_id = eid
    if "_perm_var" in eid:
        orig_id = eid.split("_perm_var")[0]
    elif "_aug_var" in eid:
        orig_id = eid.split("_aug_var")[0]
    elif "_neg_var" in eid:
        orig_id = eid.split("_neg_var")[0]
        
    if orig_id in train_original_ids:
        val_leakages += 1

print(f"\nLeakage analysis:")
print(f"  - Samples in Val: {len(val_samples)}")
print(f"  - Number of leaked samples: {val_leakages} ({val_leakages/len(val_samples)*100:.2f}%)")
