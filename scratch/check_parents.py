import json

merged_path = r"d:\mduy\source\repos\EXACT\data\processed\merged_valid.json"
with open(merged_path, "r", encoding="utf-8") as f:
    data = json.load(f)

orig_by_id = {s['example_id']: s for s in data if 'augmented' not in s.get('dataset_source', '')}
aug_mismatches = [s for s in data if 'augmented' in s.get('dataset_source', '') and len(s['premises-NL']) != len(s['premises-FOL'])]

parent_mismatched = 0
for s in aug_mismatches:
    parent_id = s['example_id'].replace('_aug', '')
    parent = orig_by_id.get(parent_id)
    if parent and len(parent['premises-NL']) != len(parent['premises-FOL']):
        parent_mismatched += 1

print(f"Total augmented mismatches: {len(aug_mismatches)}")
print(f"How many of them have mismatched parents: {parent_mismatched}")
