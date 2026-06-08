import json
from pathlib import Path
from collections import Counter

root_dir = Path(__file__).resolve().parents[1]
dataset_path = root_dir / "data" / "processed" / "logic_merged_valid_augmented.json"

with open(dataset_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total samples: {len(data)}")

# Count by split
split_counts = Counter(s.get("split", "unknown") for s in data)
print("\nSplit distribution:")
for k, v in split_counts.items():
    print(f"  - {k}: {v}")

# Count by dataset_source
source_counts = Counter(s.get("dataset_source", "unknown") for s in data)
print("\nDataset source distribution:")
for k, v in source_counts.items():
    print(f"  - {k}: {v}")
