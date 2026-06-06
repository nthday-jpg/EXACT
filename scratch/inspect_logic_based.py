import json

file_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Collect logic_based stories
logic_based_samples = [d for d in data if d.get("dataset_source") == "logic_based"]

seen_stories = set()
unique_stories = []
for s in logic_based_samples:
    prem = tuple(s.get("premises-NL"))
    if prem not in seen_stories:
        seen_stories.add(prem)
        unique_stories.append(s)

print(f"Total unique logic_based stories: {len(unique_stories)}")

for i in range(min(15, len(unique_stories))):
    s = unique_stories[i]
    print(f"\nStory {i} (Story ID: {s.get('story_id')}, Example ID: {s.get('example_id')}):")
    for p in s.get("premises-NL"):
        print(f"  - {p}")
