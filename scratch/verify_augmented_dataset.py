import json
from pathlib import Path

def main():
    augmented_path = Path("d:/mduy/source/repos/EXACT/data/processed/logic_merged_valid_augmented.json")
    print(f"Loading {augmented_path}...")
    with open(augmented_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    print(f"Total samples loaded: {len(data)}")
    
    # Check splits
    splits = {}
    for item in data:
        s = item.get("split", "unknown")
        splits[s] = splits.get(s, 0) + 1
    print("Splits count:", splits)
    
    # Check if there are synthetic samples and verify they have CoT
    synthetic_count = 0
    synthetic_with_cot = 0
    synthetic_with_expl = 0
    non_synthetic_with_cot = 0
    
    for item in data:
        # Check if it has CoT
        has_cot = "cot" in item
        has_expl = "explanation" in item
        
        # Synthetic samples typically have higher depth or particular ID/source pattern
        # Our generator assigned logic_synthetic_multihop source or we can detect via some field
        # Let's see if we have story_id starting with 'synth_logic_'
        story_id = str(item.get("story_id", ""))
        if story_id.startswith("synth_logic_"):
            synthetic_count += 1
            if has_cot:
                synthetic_with_cot += 1
            if has_expl:
                synthetic_with_expl += 1
        else:
            if has_cot:
                non_synthetic_with_cot += 1

    print(f"Synthetic samples (story_id starts with 'synth_logic_'): {synthetic_count}")
    print(f"Synthetic with cot: {synthetic_with_cot}")
    print(f"Synthetic with explanation: {synthetic_with_expl}")
    print(f"Non-synthetic with cot: {non_synthetic_with_cot}")
    
    # Verify no leaks: ensure that story_id in split="val" never appears in split="train"
    train_stories = {item.get("story_id") for item in data if item.get("split") == "train" if item.get("story_id")}
    val_stories = {item.get("story_id") for item in data if item.get("split") == "val" if item.get("story_id")}
    overlap = train_stories.intersection(val_stories)
    print(f"Train story count: {len(train_stories)}")
    print(f"Val story count: {len(val_stories)}")
    print(f"Overlap between train and val story_ids: {len(overlap)}")
    if overlap:
        print(f"WARNING: Leakage detected on story_ids: {overlap}")
    else:
        print("SUCCESS: Zero story-level leakage between train and val!")

if __name__ == "__main__":
    main()
