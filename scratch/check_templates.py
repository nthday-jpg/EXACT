import json
import os
import re
from collections import Counter

file_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total samples: {len(data)}")

# Let's group by dataset_source
by_source = {}
for d in data:
    src = d.get("dataset_source")
    if src not in by_source:
        by_source[src] = []
    by_source[src].append(d)

for src, samples in by_source.items():
    print(f"\n=================== SOURCE: {src} (Total: {len(samples)}) ===================")
    # Unique stories defined by story_id
    stories = set(s.get("story_id") for s in samples)
    print(f"Number of unique story_ids: {len(stories)}")
    
    # Unique stories defined by premises-NL
    premises_tuples = set(tuple(s.get("premises-NL")) for s in samples)
    print(f"Number of unique premises-NL lists: {len(premises_tuples)}")
    
    # Let's count how many samples have MCQs (question contains options or answer is A, B, C, D)
    answers = [s.get("answer") for s in samples]
    answers_counter = Counter(answers)
    print("Answers distribution:", dict(answers_counter))
    
    # Check if questions have choices like A., B., C., D. or A), B), C), D)
    mcq_count = 0
    for s in samples:
        q = s.get("question", "")
        if re.search(r'\b[A-D][\.\)]', q) or s.get("answer") in ['A', 'B', 'C', 'D']:
            mcq_count += 1
    print(f"MCQ samples: {mcq_count} / {len(samples)}")
    print(f"Non-MCQ samples (Yes/No/Uncertain/True/False/Unknown): {len(samples) - mcq_count}")
    
    # Inspect explanations
    explanations = [s.get("explanation") for s in samples]
    non_null_exp = sum(1 for e in explanations if e is not None)
    print(f"Non-null explanations: {non_null_exp} / {len(samples)}")
    
    # Let's print the first 5 unique stories to see their text style
    print("\nFirst 3 unique stories:")
    unique_stories_seen = set()
    count = 0
    for s in samples:
        prem_tuple = tuple(s.get("premises-NL"))
        if prem_tuple not in unique_stories_seen:
            unique_stories_seen.add(prem_tuple)
            count += 1
            print(f"  Story {count} (ID {s.get('story_id')}):")
            for p in s.get("premises-NL"):
                print(f"    - {p}")
            if count >= 3:
                break
