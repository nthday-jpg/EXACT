#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

def main():
    print("=" * 80)
    print("AUDITING BASELINE DATASET PREMISE SET (STORY) UNIQUENESS")
    print("=" * 80)

    data_dir = root_dir / "data" / "processed"
    base_file = data_dir / "logic_merged_valid.json"

    if not base_file.exists():
        print(f"Error: Base dataset file {base_file} not found.")
        sys.exit(1)

    print(f"Loading baseline dataset from {base_file.name}...")
    with open(base_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    total_samples = len(dataset)
    print(f"Total samples in dataset: {total_samples}")

    # 1. Group samples by identical premise sets (represented as newline-joined string)
    premise_to_samples = defaultdict(list)
    for sample in dataset:
        prems = sample.get("premises-NL", [])
        # Clean/normalize whitespace inside each premise to prevent false differences due to formatting
        cleaned_prems = tuple(p.strip() for p in prems)
        premise_to_samples[cleaned_prems].append(sample)

    unique_premise_sets = len(premise_to_samples)
    print(f"Total unique premise sets (stories): {unique_premise_sets}")

    # 2. Analyze frequency distribution of samples per premise set
    counts = [len(samples) for samples in premise_to_samples.values()]
    distribution = Counter(counts)

    print("-" * 60)
    print("Frequency Distribution of Samples (Questions) per Premise Set:")
    for num_samples, freq in sorted(distribution.items()):
        percentage = (freq * num_samples / total_samples) * 100
        print(f"  - {freq} premise sets have exactly {num_samples} sample(s) ({freq * num_samples} samples total, {percentage:.2f}%)")

    # 3. Check for story_id consistency
    # (a) Check if the same unique premise set maps to multiple different story_ids
    premise_to_story_ids = defaultdict(set)
    for prems, samples in premise_to_samples.items():
        for s in samples:
            story_id = s.get("story_id", "missing")
            premise_to_story_ids[prems].add(str(story_id))

    multi_mapped_premises = {prems: sids for prems, sids in premise_to_story_ids.items() if len(sids) > 1}

    # (b) Check if the same story_id maps to multiple different premise sets
    story_id_to_premises = defaultdict(set)
    for prems, samples in premise_to_samples.items():
        for s in samples:
            story_id = s.get("story_id", "missing")
            story_id_to_premises[str(story_id)].add(prems)

    multi_mapped_stories = {sid: prems_set for sid, prems_set in story_id_to_premises.items() if len(prems_set) > 1}

    print("-" * 60)
    print("3. Story ID Mapping Consistency Audit:")
    
    # Report if one premise set maps to different story_ids
    if multi_mapped_premises:
        print(f"  [WARNING] Found {len(multi_mapped_premises)} unique premise set(s) mapped to MULTIPLE different story_ids!")
        for idx, (prems, sids) in enumerate(list(multi_mapped_premises.items())[:5]):
            print(f"    - Premise set maps to story_ids: {sorted(list(sids))}")
            print(f"      First premise snippet: \"{prems[0] if prems else 'None'}\"")
        if len(multi_mapped_premises) > 5:
            print(f"    ... and {len(multi_mapped_premises) - 5} more.")
    else:
        print("  [SUCCESS] All unique premise sets map to exactly one story_id!")

    # Report if one story_id has multiple different premise sets
    if multi_mapped_stories:
        print(f"  [WARNING] Found {len(multi_mapped_stories)} story_id(s) containing MULTIPLE different premise sets!")
        for idx, (sid, prems_set) in enumerate(list(multi_mapped_stories.items())[:5]):
            print(f"    - story_id \"{sid}\" contains {len(prems_set)} different premise sets!")
            # Print a snippet of first premises
            for p_idx, p in enumerate(list(prems_set)[:2]):
                print(f"      Set {p_idx+1} first premise: \"{p[0] if p else 'None'}\"")
        if len(multi_mapped_stories) > 5:
            print(f"    ... and {len(multi_mapped_stories) - 5} more.")
    else:
        print("  [SUCCESS] All story_ids contain strictly consistent premise sets!")

    print("=" * 80)
    print("AUDIT VERDICT:")
    if not multi_mapped_premises and not multi_mapped_stories:
        print("  [CLEAN] Premise sets and Story IDs are perfectly aligned 1:1.")
    else:
        print("  [WARNING] Minor structure discrepancies identified between premise sets and story_ids.")
    print("=" * 80)

if __name__ == "__main__":
    main()
