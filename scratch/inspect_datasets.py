import json

def inspect_json(filepath):
    print(f"--- Inspecting {filepath} ---")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Total elements: {len(data)}")
    if len(data) > 0:
        sample = data[0]
        print("Keys:", list(sample.keys()))
        print("Sample:", json.dumps(sample, indent=2))

inspect_json(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json")
print()
try:
    inspect_json(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json")
except Exception as e:
    print("Error reading augmented file:", e)
