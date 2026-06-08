import json

def get_all_keys(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    keys = set()
    for item in data:
        keys.update(item.keys())
    print(f"{filepath} unique keys: {sorted(list(keys))}")

get_all_keys(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json")
get_all_keys(r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json")
