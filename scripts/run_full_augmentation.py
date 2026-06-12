#!/usr/bin/env python3
import os
import sys
import json
import random
import time
import re
from pathlib import Path
from collections import defaultdict
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

def normalize_fol(formula):
    # Standardize spaces and keep logic keywords
    keywords = {"ForAll", "Exists", "AND", "OR", "NOT", "In", "->", "<->", "=", "!=", ">=", "<=", ">", "<"}
    # Extract all word-like identifiers
    words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_-]*\b", formula)
    word_map = {}
    counter = 0
    normalized = formula
    for w in words:
        if w in keywords or w.isdigit() or w.startswith("VAR_"):
            continue
        if w not in word_map:
            word_map[w] = f"VAR_{counter}"
            counter += 1
        normalized = re.sub(r"\b" + re.escape(w) + r"\b", word_map[w], normalized)
    return normalized

def get_structure_key(sample):
    fol_list = sample.get("premises-FOL", [])
    normalized_list = [normalize_fol(f) for f in fol_list]
    return "||".join(normalized_list)

def main():
    print("=" * 80)
    print("RUNNING SPLIT-FIRST DATA AUGMENTATION PIPELINE (ZERO LEAKAGE, FIXED BUDGET)")
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

    # De-duplicate original samples first using user-provided logic
    unique_originals = []
    seen_premises = set()
    for item in original_data:
        nl_list = item.get("premises-NL", [])
        fol_list = item.get("premises-FOL", [])
        if not nl_list or not fol_list or len(nl_list) != len(fol_list):
            continue
        nl_serialized = "\n".join(nl_list)
        if nl_serialized in seen_premises:
            continue
        seen_premises.add(nl_serialized)
        
        # Build the unique sample preserving all fields (for compatibility with augmenters)
        unique_sample = item.copy()
        unique_originals.append(unique_sample)

    print(f"Loaded {len(unique_originals)} unique translation samples from {input_file.name}")

    # 1. Apply Quantifier Variable Canonicalization to the unique original samples
    print("\n[1/5] Applying Quantifier Variable Canonicalization...")
    canonicalizer = QuantifiedVariableCanonicalizer()
    canonicalized_originals = []
    for s in unique_originals:
        canonicalized_originals.append(canonicalizer.canonicalize_sample(s))
    print(f"  -> Canonicalized {len(canonicalized_originals)} unique original samples.")

    # 2. Perform Grouped Train/Val Split (No-Leakage) using structure keys or existing splits
    print("\n[2/5] Performing Grouped Story-level Split (Preserving existing splits if possible)...")
    
    # Load existing split mapping if available to ensure split stability
    split_mapping = {}
    if output_file.exists():
        try:
            with open(output_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                for item in existing_data:
                    eid = item.get("example_id", "").replace("_canonical", "")
                    if "split" in item and eid:
                        split_mapping[eid] = item["split"]
            print(f"  -> Loaded {len(split_mapping)} split mappings from existing {output_file.name}")
        except Exception as e:
            print(f"  -> Warning: Could not load existing split mapping: {e}")

    groups = defaultdict(list)
    for sample in canonicalized_originals:
        key = get_structure_key(sample)
        groups[key].append(sample)

    unique_keys = sorted(list(groups.keys()))
    # Deterministic shuffle
    rng = random.Random(42)
    rng.shuffle(unique_keys)

    # 90/10 split (fallback)
    split_idx = int(len(unique_keys) * 0.9)
    train_keys = set(unique_keys[:split_idx])
    val_keys = set(unique_keys[split_idx:])

    train_originals = []
    val_originals = []
    
    for key in unique_keys:
        samples = groups[key]
        
        # Determine split based on existing split mapping
        split_counts = defaultdict(int)
        for s in samples:
            eid = s.get("example_id", "").replace("_canonical", "")
            if eid in split_mapping:
                split_counts[split_mapping[eid]] += 1
                
        if split_counts.get("val", 0) > split_counts.get("train", 0):
            group_split = "val"
        elif split_counts.get("train", 0) > split_counts.get("val", 0):
            group_split = "train"
        else:
            # Fallback to dynamic split if not in mapping
            group_split = "val" if key in val_keys else "train"
            
        for s in samples:
            s_copy = s.copy()
            s_copy["split"] = group_split
            if group_split == "val":
                val_originals.append(s_copy)
            else:
                train_originals.append(s_copy)

    print(f"  -> Train original samples: {len(train_originals)}")
    print(f"  -> Val original samples:   {len(val_originals)}")

    final_dataset = []
    # Add validation samples as-is (they are already canonicalized and tagged)
    final_dataset.extend(val_originals)
    # Add training original samples
    final_dataset.extend(train_originals)

    # 3. Entity Anonymization (~50% of train samples, exactly 1 variant)
    print("\n[3/5] Applying Entity Anonymization (Target: 50% of train originals, 1 variant)...")
    anonymizer = EntityAnonymizer()
    anonymized_count = 0
    
    # Shuffle training originals to try anonymization in random order
    train_pool = list(train_originals)
    rng.shuffle(train_pool)
    target_anon = len(train_originals) // 2
    
    for s in train_pool:
        if anonymized_count >= target_anon:
            break
        try:
            # Generate exactly 1 variant (variant_idx=0) using mix strategy
            aug = anonymizer.anonymize_sample(s, strategy="mix", variant_idx=0)
            if aug:
                aug_canon = canonicalizer.canonicalize_sample(aug)
                aug_canon["split"] = "train"
                final_dataset.append(aug_canon)
                anonymized_count += 1
        except Exception as e:
            pass
    print(f"  -> Generated {anonymized_count} Entity Anonymization samples.")

    # 4. Multi-Premise Permutation (1 variant, only stories with >= 4 premises in train)
    print("\n[4/5] Applying Multi-Premise Permutation (1 variant, >= 4 premises)...")
    permuter = MultiPremisePermuter()
    permutation_count = 0
    for s in train_originals:
        if len(s.get("premises-NL", [])) >= 4:
            try:
                # Generate exactly 1 permutation variant (variant_idx=0)
                aug = permuter.permute_sample(s, variant_idx=0)
                if aug:
                    aug_canon = canonicalizer.canonicalize_sample(aug)
                    aug_canon["split"] = "train"
                    final_dataset.append(aug_canon)
                    permutation_count += 1
            except Exception as e:
                pass
    print(f"  -> Generated {permutation_count} Multi-Premise Permutation samples.")

    # 5. Hard Negative Augmentation (20% of train size, 1 variant)
    target_negatives = int(len(train_originals) * 0.20)
    print(f"\n[5/5] Applying Hard Negative Augmentation (Target: {target_negatives} samples)...")

    # Shuffle training originals to select target subset randomly
    shuffled_pool = list(train_originals)
    rng.shuffle(shuffled_pool)

    augmenter = HardNegativeAugmenter()
    hard_negatives = []
    
    pool_idx = 0
    tried_count = 0

    # Helper function to run augmentation for a single sample (without Z3 validation in threads)
    def process_sample(sample_info):
        sample, idx = sample_info
        res = augmenter.augment_sample(sample, variant_idx=0, validate_z3=False)
        if res:
            res_canon = canonicalizer.canonicalize_sample(res)
            res_canon["split"] = "train"
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
                            break
                    else:
                        print(f"    [Z3 Skip] Generated FOL failed validation: {err}")

    final_dataset.extend(hard_negatives)
    print(f"  -> Generated {len(hard_negatives)} valid Hard Negative samples (Tried {tried_count} candidates).")

    # Load synthetic multi-hop dataset if it exists
    synthetic_file = data_dir / "logic_synthetic_multihop.json"
    synthetic_count = 0
    if synthetic_file.exists():
        print(f"\nLoading synthetic multi-hop logic samples from: {synthetic_file.name}...")
        with open(synthetic_file, "r", encoding="utf-8") as f:
            synthetic_data = json.load(f)
        
        canonicalized_synthetic = []
        for s in synthetic_data:
            s_canon = canonicalizer.canonicalize_sample(s)
            s_canon["split"] = "train"
            # Preserve optional fields like CoT and explanation
            if "cot" in s:
                s_canon["cot"] = s["cot"]
            if "explanation" in s:
                s_canon["explanation"] = s["explanation"]
            canonicalized_synthetic.append(s_canon)
            
        final_dataset.extend(canonicalized_synthetic)
        synthetic_count = len(canonicalized_synthetic)
        print(f"  -> Added {synthetic_count} synthetic multi-hop samples to final dataset.")

    # Save final dataset
    print(f"\nSaving {len(final_dataset)} total samples to {output_file.name}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("DATASET AUGMENTATION COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Original samples:               {len(original_data)}")
    print(f"Train originals (canonicalized):{len(train_originals)}")
    print(f"Val originals (canonicalized):  {len(val_originals)}")
    print(f"Entity Anonymization (Train):   {anonymized_count}")
    print(f"Multi-Premise Permutation(Train):{permutation_count}")
    print(f"Hard Negative (Train):          {len(hard_negatives)}")
    print(f"Synthetic Multi-Hop (Train):     {synthetic_count}")
    print("-" * 80)
    print(f"Total Combined Output Size:     {len(final_dataset)}")
    print(f"Target Expansion Factor:        {len(final_dataset)/len(original_data):.2f}x")
    print("=" * 80)

if __name__ == "__main__":
    main()
