#!/usr/bin/env python3
import os
import sys
import json
import random
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root directory to sys.path to enable top-level imports from 'src'
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.data.augmentation import (
    QuantifiedVariableCanonicalizer,
    EntityAnonymizer,
    MultiPremisePermuter,
    HardNegativeAugmenter
)
from src.data.augmentation.hard_negative_augmenter import validate_fol_formulas

def main():
    print("=" * 80)
    print("RUNNING FULL DATA AUGMENTATION PIPELINE (WITH QUANTITY CONTROL)")
    print("=" * 80)

    # Set random seeds for reproducibility
    random.seed(42)

    data_dir = root_dir / "data" / "processed"
    input_file = data_dir / "logic_merged_valid.json"
    output_file = data_dir / "logic_merged_valid_augmented.json"

    if not input_file.exists():
        print(f"Error: Could not find input file at {input_file}")
        sys.exit(1)

    print(f"Loading original dataset from: {input_file.name}...")
    with open(input_file, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    print(f"Loaded {len(original_data)} original samples.")

    # 1. Quantifier Variable Canonicalization (100% of original dataset)
    print("\n[1/4] Applying Quantifier Variable Canonicalization to original samples...")
    canonicalizer = QuantifiedVariableCanonicalizer()
    canonicalized_originals = []
    for s in original_data:
        canonicalized_originals.append(canonicalizer.canonicalize_sample(s))
    print(f"  -> Canonicalized {len(canonicalized_originals)} original samples.")

    final_dataset = list(canonicalized_originals)

    # 2. Entity Anonymization (3 variants per story)
    print("\n[2/4] Applying Entity Anonymization (3 variants per story)...")
    anonymizer = EntityAnonymizer()
    anonymized_count = 0
    for s in canonicalized_originals:
        for i in range(3):
            try:
                aug = anonymizer.anonymize_sample(s, strategy="mix", variant_idx=i)
                if aug:
                    # Canonicalize the augmented output
                    aug_canon = canonicalizer.canonicalize_sample(aug)
                    final_dataset.append(aug_canon)
                    anonymized_count += 1
            except Exception as e:
                pass
    print(f"  -> Generated {anonymized_count} Entity Anonymization samples.")

    # 3. Multi-Premise Permutation (2 variants per story, only stories with >= 4 premises)
    print("\n[3/4] Applying Multi-Premise Permutation (2 variants per story, >= 4 premises)...")
    permuter = MultiPremisePermuter()
    permutation_count = 0
    for s in canonicalized_originals:
        if len(s.get("premises-NL", [])) >= 4:
            for i in range(2):
                try:
                    aug = permuter.permute_sample(s, variant_idx=i)
                    if aug:
                        # Canonicalize the augmented output
                        aug_canon = canonicalizer.canonicalize_sample(aug)
                        final_dataset.append(aug_canon)
                        permutation_count += 1
                except Exception as e:
                    pass
    print(f"  -> Generated {permutation_count} Multi-Premise Permutation samples.")

    # 4. Hard Negative Augmentation (10% of original dataset size = 181 samples)
    target_negatives = int(len(original_data) * 0.10)
    print(f"\n[4/4] Applying Hard Negative Augmentation (Target: {target_negatives} samples)...")

    # Shuffle original samples to select target subset randomly
    shuffled_pool = list(canonicalized_originals)
    random.shuffle(shuffled_pool)

    augmenter = HardNegativeAugmenter()
    hard_negatives = []
    
    pool_idx = 0
    tried_count = 0

    # Helper function to run augmentation for a single sample (without Z3 validation in threads)
    def process_sample(sample_info):
        sample, idx = sample_info
        res = augmenter.augment_sample(sample, variant_idx=0, validate_z3=False)
        if res:
            # Canonicalize it to ensure correctness (regex-based, no Z3)
            res_canon = canonicalizer.canonicalize_sample(res)
            return res_canon
        return None

    # Call LLM concurrently using ThreadPoolExecutor
    max_workers = 10
    print(f"Running LLM augmentation concurrently with {max_workers} workers...")
    
    while len(hard_negatives) < target_negatives and pool_idx < len(shuffled_pool):
        needed = target_negatives - len(hard_negatives)
        batch_size = min(int(needed * 1.2) + 2, len(shuffled_pool) - pool_idx)
        if batch_size <= 0:
            break
            
        batch_samples = [(shuffled_pool[pool_idx + k], pool_idx + k) for k in range(batch_size)]
        pool_idx += batch_size
        tried_count += batch_size

        print(f"  - Launching batch of {batch_size} samples (Total succeeded: {len(hard_negatives)}/{target_negatives})...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_sample, item): item for item in batch_samples}
            for fut in as_completed(futures):
                res = fut.result()
                if res:
                    # Validate FOL formulas sequentially on the main thread
                    is_valid, err = validate_fol_formulas(res["premises-FOL"])
                    if is_valid:
                        hard_negatives.append(res)
                        if len(hard_negatives) >= target_negatives:
                            # Cancel pending or wait, but break out of the loop
                            break
                    else:
                        print(f"    [Z3 Skip] Generated FOL failed validation: {err}")


    final_dataset.extend(hard_negatives)
    print(f"  -> Generated {len(hard_negatives)} valid Hard Negative samples (Tried {tried_count} candidates).")

    # Save final dataset
    print(f"\nSaving {len(final_dataset)} total samples to {output_file.name}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("DATASET AUGMENTATION COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Original samples:               {len(original_data)}")
    print(f"Canonicalized original samples: {len(canonicalized_originals)}")
    print(f"Entity Anonymization:           {anonymized_count}")
    print(f"Multi-Premise Permutation:      {permutation_count}")
    print(f"Hard Negative Augmentation:     {len(hard_negatives)}")
    print("-" * 80)
    print(f"Total Combined Output Size:     {len(final_dataset)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
