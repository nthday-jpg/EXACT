import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

val_count = sum(1 for item in data if item.get("split") == "val")
print(f"Total samples with split=='val': {val_count}")

# Distribution of dataset_source for split=="val"
sources = {}
for item in data:
    if item.get("split") == "val":
        src = item.get("dataset_source", "unknown")
        sources[src] = sources.get(src, 0) + 1

print("Dataset source distribution for validation split:")
for src, count in sources.items():
    print(f"  - {src}: {count}")
