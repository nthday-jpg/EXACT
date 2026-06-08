import json
from collections import Counter

def analyze_json(filepath):
    print(f"=== Analysis for {filepath} ===")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Total items: {len(data)}")
    
    sources = Counter(item.get("dataset_source") for item in data)
    print("Dataset Sources:")
    for src, cnt in sources.items():
        print(f"  - {src}: {cnt}")
        
    splits = Counter(item.get("split") for item in data)
    if any(splits.values()):
        print("Splits:")
        for sp, cnt in splits.items():
            print(f"  - {sp}: {cnt}")
            
    # Check what dataset sources are present in each split
    if "split" in data[0]:
        print("Split vs Source distribution:")
        dist = Counter((item.get("split"), item.get("dataset_source")) for item in data)
        for (sp, src), cnt in sorted(dist.items()):
            print(f"  - Split '{sp}', Source '{src}': {cnt}")

analyze_json(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json")
print()
analyze_json(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json")
