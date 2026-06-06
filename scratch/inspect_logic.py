import json
import os
from collections import Counter

file_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total samples: {len(data)}")
print("Sample keys:", list(data[0].keys()) if data else "Empty")

sources = Counter(d.get("dataset_source") for d in data)
print("\nDataset Sources distribution:")
for source, count in sources.items():
    print(f"  - {source}: {count}")

# Check some samples from each source
samples_by_source = {}
for d in data:
    src = d.get("dataset_source")
    if src not in samples_by_source:
        samples_by_source[src] = []
    if len(samples_by_source[src]) < 2:
        samples_by_source[src].append(d)

print("\nSample instances per source:")
for src, samples in samples_by_source.items():
    print(f"\n--- Source: {src} ---")
    for s in samples:
        print(f"Story ID: {s.get('story_id')}, Example ID: {s.get('example_id')}")
        print(f"Premises-NL: {s.get('premises-NL')[:2]}")
        print(f"Premises-FOL: {s.get('premises-FOL')[:2]}")
        print(f"Question: {s.get('question')}")
        print(f"Answer: {s.get('answer')}")
