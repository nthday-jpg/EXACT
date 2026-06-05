import json
from pathlib import Path

data_dir = Path(r"d:\mduy\source\repos\EXACT\data")
processed_dir = data_dir / "processed"

files_to_check = [
    (data_dir, "folio-train.json"),
    (data_dir, "logic_based.json"),
    (processed_dir, "folio-train.json"),
    (processed_dir, "logic_based.json"),
    (processed_dir, "logic_merged_valid.json"),
    (processed_dir, "logic_merged_valid_entity_anonymized.json"),
    (processed_dir, "logic_merged_valid_multi_premise_permuted.json"),
    (processed_dir, "logic_merged_valid_quantified_variable_renamed.json"),
    (processed_dir, "logic_merged_valid_quantified_variable_canonicalized.json"),
    (processed_dir, "logic_merged_valid_commutative_reordered.json"),
    (processed_dir, "logic_merged_valid_premise_subset_generated.json"),
]

for parent_dir, file_name in files_to_check:
    file_path = parent_dir / file_name
    if not file_path.exists():
        print(f"{file_name} in {parent_dir.name} does not exist.")
        continue
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    mismatched = []
    for idx, sample in enumerate(data):
        nl = sample.get("premises-NL", [])
        fol = sample.get("premises-FOL", [])
        if len(nl) != len(fol):
            mismatched.append((idx, sample.get("example_id", sample.get("story_id")), len(nl), len(fol)))
            
    print(f"File: {parent_dir.name}/{file_name}")
    print(f"  Total samples: {len(data)}")
    print(f"  Mismatched samples: {len(mismatched)}")
    if mismatched:
        print(f"  First few mismatched: {mismatched[:5]}")
    print("-" * 50)

