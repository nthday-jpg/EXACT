#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path

# Add project root directory to sys.path to enable top-level imports from 'src'
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

try:
    from src.data.augmentation.entity_anonymizer import EntityAnonymizer
except ImportError as e:
    print(f"Error importing EntityAnonymizer: {e}")
    print("Please make sure you are running this script inside the project virtual environment.")
    sys.exit(1)


def main():
    print("=" * 80)
    print("DATASET ENTITY ANONYMIZATION & PERMUTATION AUGMENTATION")
    print("=" * 80)

    data_dir = root_dir / "data" / "processed"
    merged_file = data_dir / "merged_valid.json"

    if not merged_file.exists():
        print(f"Error: Could not find dataset file at {merged_file}")
        sys.exit(1)

    print(f"Loading dataset from: {merged_file.name}...")
    with open(merged_file, "r", encoding="utf-8") as f:
        try:
            dataset = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON from {merged_file}: {e}")
            sys.exit(1)

    print(f"Loaded {len(dataset)} total samples.")

    # Filter out already augmented samples to ensure idempotency
    original_samples = [s for s in dataset if "augmented" not in str(s.get("dataset_source", ""))]
    already_augmented_count = len(dataset) - len(original_samples)
    
    print(f"  - Original valid samples to process: {len(original_samples)}")
    if already_augmented_count > 0:
        print(f"  - Already augmented samples present: {already_augmented_count} (skipping to prevent double augmentation)")

    if len(original_samples) == 0:
        print("No new original samples found for augmentation. Exiting.")
        sys.exit(0)

    anonymizer = EntityAnonymizer()
    augmented_samples = []

    print("\nRunning Entity Anonymization & Permutation...")
    success_count = 0
    failure_count = 0

    for idx, sample in enumerate(original_samples):
        # We use "mix" strategy: 50% letters, 50% random names
        try:
            aug_sample = anonymizer.anonymize_sample(sample, strategy="mix")
            if aug_sample:
                augmented_samples.append(aug_sample)
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to augment sample at index {idx} (ID: {sample.get('example_id', 'unknown')}): {e}")
            failure_count += 1

    print(f"\nAugmentation completed:")
    print(f"  - Successfully augmented: {success_count} samples")
    print(f"  - Skipped (no standard constants found): {failure_count} samples")

    # Combine original and the newly generated deterministic augmented samples
    combined_dataset = original_samples + augmented_samples

    print(f"\nSaving {len(combined_dataset)} total samples back to {merged_file.name}...")
    
    # Save the updated dataset back
    with open(merged_file, "w", encoding="utf-8") as f:
        json.dump(combined_dataset, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("AUGMENTATION PIPELINE FINISHED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
