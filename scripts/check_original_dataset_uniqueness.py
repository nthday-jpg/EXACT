#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from collections import Counter

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

def main():
    print("=" * 80)
    print("AUDITING BASELINE DATASET UNIQUENESS")
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

    # 1. Check for Duplicate IDs (example_id)
    example_ids = [s.get("example_id", "") for s in dataset]
    id_counts = Counter(example_ids)
    duplicate_ids = {eid: count for eid, count in id_counts.items() if count > 1}

    # 2. Check for Duplicate Content (premises-NL + question)
    # Use a serialized representation as key
    content_keys = []
    for s in dataset:
        prems = "".join(sorted(s.get("premises-NL", [])))
        question = s.get("question", "")
        content_keys.append((prems, question))
        
    content_counts = Counter(content_keys)
    duplicate_contents = {key: count for key, count in content_counts.items() if count > 1}

    print("-" * 60)
    print("1. Duplicate ID Audit:")
    if duplicate_ids:
        print(f"  [WARNING] Found {len(duplicate_ids)} duplicate example_id(s)!")
        for eid, count in list(duplicate_ids.items())[:10]:
            print(f"    - ID: {eid} appears {count} times")
        if len(duplicate_ids) > 10:
            print(f"    ... and {len(duplicate_ids) - 10} more.")
    else:
        print("  [SUCCESS] All example_ids are strictly unique!")

    print("-" * 60)
    print("2. Duplicate Content Audit (Identical Premises + Question):")
    if duplicate_contents:
        print(f"  [WARNING] Found {len(duplicate_contents)} identical content group(s)!")
        # Find sample IDs for the duplicates to be helpful
        for (prems, question), count in list(duplicate_contents.items())[:5]:
            matching_ids = [s.get("example_id", "") for s in dataset if "".join(sorted(s.get("premises-NL", []))) == prems and s.get("question", "") == question]
            print(f"    - Content appears {count} times. Associated IDs: {matching_ids}")
            print(f"      Question: \"{question}\"")
        if len(duplicate_contents) > 5:
            print(f"    ... and {len(duplicate_contents) - 5} more duplicate groups.")
    else:
        print("  [SUCCESS] All samples have unique contents!")

    print("=" * 80)
    print("AUDIT SUMMARY:")
    print(f"  - Total Samples: {total_samples}")
    print(f"  - Unique IDs: {len(id_counts)}")
    print(f"  - Unique Content Pairs: {len(content_counts)}")
    
    if not duplicate_ids and not duplicate_contents:
        print("\n  [VERDICT] The original dataset is 100% clean and unique!")
    else:
        print("\n  [VERDICT] The original dataset contains duplicates that should be kept in mind.")
    print("=" * 80)

if __name__ == "__main__":
    main()
