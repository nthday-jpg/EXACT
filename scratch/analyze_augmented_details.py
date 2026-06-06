import json
from collections import Counter, defaultdict

original_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"
augmented_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json"

with open(original_path, 'r', encoding='utf-8') as f:
    orig_data = json.load(f)

with open(augmented_path, 'r', encoding='utf-8') as f:
    aug_data = json.load(f)

print(f"Original samples count: {len(orig_data)}")
print(f"Augmented samples count: {len(aug_data)}")
print(f"Expansion factor: {len(aug_data) / len(orig_data):.2f}x")

# Analyze by source
orig_sources = Counter(s.get("dataset_source", "unknown") for s in orig_data)
aug_sources = Counter(s.get("dataset_source", "unknown") for s in aug_data)

print("\n=== Original Sources ===")
for src, count in orig_sources.items():
    print(f"  - {src}: {count}")

print("\n=== Augmented Sources ===")
# Group augmented sources by categories:
# 1. Original (or canonicalized)
# 2. Entity Anonymization (contains 'augmented-letters' or 'augmented-names')
# 3. Permutation (contains 'augmented-permutation')
# 4. Hard Negative (contains 'augmented-negative')
categories = defaultdict(int)
for s in aug_data:
    src = s.get("dataset_source", "unknown")
    if "augmented" not in src:
        categories["Original"] += 1
    elif "canonicalized" in src and "augmented" not in src:
        categories["Original (Canonicalized)"] += 1
    elif "augmented-letters" in src or "augmented-names" in src:
        categories["Entity Anonymization"] += 1
    elif "augmented-permutation" in src:
        categories["Multi-Premise Permutation"] += 1
    elif "augmented-negative" in src:
        categories["Hard Negative"] += 1
    else:
        categories[f"Other ({src})"] += 1

for cat, count in categories.items():
    print(f"  - {cat}: {count} ({count/len(orig_data)*100:.2f}% of original size)")

# Let's check story level uniqueness and overlaps
# A story is uniquely identified by its premises-NL (ignoring normalization)
# Let's count original stories
orig_stories = set()
for s in orig_data:
    premises = tuple(p.strip().lower() for p in s.get("premises-NL", []))
    orig_stories.add(premises)

print(f"\nUnique stories in original dataset: {len(orig_stories)}")

# Let's investigate the splitting logic and see if there is potential leakage
# Specifically, let's normalize FOL and see the keys
def normalize_fol(formula):
    import re
    keywords = {"ForAll", "Exists", "AND", "OR", "NOT", "In", "->", "<->", "=", "!=", ">=", "<=", ">", "<"}
    words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_-]*\b", formula)
    word_map = {}
    counter = 0
    normalized = formula
    for w in words:
        if w in keywords or w.isdigit() or w.startswith("VAR_"):
            continue
        if w not in word_map:
            word_map[w] = f"VAR_{counter}"
            counter += 1
        normalized = re.sub(r"\b" + re.escape(w) + r"\b", word_map[w], normalized)
    return normalized

def get_structure_key(sample):
    fol_list = sample.get("premises-FOL", [])
    normalized_list = [normalize_fol(f) for f in fol_list]
    return "||".join(normalized_list)

# Group augmented dataset by structure key
groups = defaultdict(list)
for s in aug_data:
    key = get_structure_key(s)
    groups[key].append(s)

print(f"Number of unique structure keys in augmented dataset: {len(groups)}")

# Let's see if any structure key has both original samples and permutation samples
# and if the permutation samples have a DIFFERENT structure key
permutation_samples = [s for s in aug_data if "augmented-permutation" in s.get("dataset_source", "")]
print(f"Total permutation samples: {len(permutation_samples)}")

mismatched_keys = 0
for p_sample in permutation_samples:
    # Find original story
    # The example_id of permutation is like {orig_id}_perm_var{idx}
    eid = p_sample.get("example_id", "")
    orig_id = eid
    if "_perm_var" in eid:
        orig_id = eid.split("_perm_var")[0]
    elif "_aug_var" in eid:
        orig_id = eid.split("_aug_var")[0]
        
    # Find original sample with this orig_id
    orig_sample = next((s for s in orig_data if str(s.get("example_id")) == orig_id), None)
    if orig_sample:
        orig_key = get_structure_key(orig_sample)
        p_key = get_structure_key(p_sample)
        if orig_key != p_key:
            mismatched_keys += 1

print(f"Permutation samples where structure key is DIFFERENT from original: {mismatched_keys} / {len(permutation_samples)}")

# --- Simulate prepare_hf_dataset Split ---
import random
seed = 42
test_size = 0.1

groups = defaultdict(list)
for sample in aug_data:
    key = get_structure_key(sample)
    groups[key].append(sample)

unique_keys = sorted(list(groups.keys()))
rng = random.Random(seed)
rng.shuffle(unique_keys)

split_idx = int(len(unique_keys) * (1 - test_size))
train_keys = set(unique_keys[:split_idx])
val_keys = set(unique_keys[split_idx:])

train_samples = []
val_samples = []
for key in unique_keys:
    if key in val_keys:
        val_samples.extend(groups[key])
    else:
        train_samples.extend(groups[key])

print(f"\n--- Simulated Split ---")
print(f"Train samples count: {len(train_samples)}")
print(f"Val samples count: {len(val_samples)}")

# Count augmented samples in val_samples
val_source_counts = Counter(s.get("dataset_source", "unknown") for s in val_samples)
print("\nValidation Dataset composition by source:")
val_aug_categories = defaultdict(int)
for s in val_samples:
    src = s.get("dataset_source", "unknown")
    if "augmented" not in src:
        val_aug_categories["Original"] += 1
    elif "augmented-letters" in src or "augmented-names" in src:
        val_aug_categories["Entity Anonymization"] += 1
    elif "augmented-permutation" in src:
        val_aug_categories["Multi-Premise Permutation"] += 1
    elif "augmented-negative" in src:
        val_aug_categories["Hard Negative"] += 1
    else:
        val_aug_categories[f"Other ({src})"] += 1

for cat, count in val_aug_categories.items():
    print(f"  - {cat}: {count} ({count/len(val_samples)*100:.2f}%)")

# Check leakages:
# 1. An original sample is in val, but its permutation or anonymized version is in train.
# 2. Or vice versa.
print("\n--- Leakage Analysis ---")
train_original_ids = set()
for s in train_samples:
    eid = s.get("example_id", "")
    orig_id = eid
    if "_perm_var" in eid:
        orig_id = eid.split("_perm_var")[0]
    elif "_aug_var" in eid:
        orig_id = eid.split("_aug_var")[0]
    train_original_ids.add(orig_id)

val_leakages = 0
for s in val_samples:
    eid = s.get("example_id", "")
    orig_id = eid
    if "_perm_var" in eid:
        orig_id = eid.split("_perm_var")[0]
    elif "_aug_var" in eid:
        orig_id = eid.split("_aug_var")[0]
    
    if orig_id in train_original_ids:
        val_leakages += 1

print(f"Number of samples in Validation Set whose original/augmented equivalents are in Training Set: {val_leakages} / {len(val_samples)} ({val_leakages/len(val_samples)*100:.2f}%)")

