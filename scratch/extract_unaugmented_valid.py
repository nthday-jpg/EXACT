import json
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parents[1]
    data_dir = root_dir / "data" / "processed"
    merged_file = data_dir / "merged_valid.json"
    output_file = data_dir / "merged_valid_no_augmentation.json"

    if not merged_file.exists():
        print(f"Error: Could not find dataset file at {merged_file}")
        return

    print(f"Loading dataset from {merged_file.name}...")
    with open(merged_file, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} total samples.")

    # Filter out augmented samples
    original_samples = [s for s in dataset if "augmented" not in str(s.get("dataset_source", ""))]
    augmented_count = len(dataset) - len(original_samples)

    print(f"Filtering stats:")
    print(f"  - Original valid samples: {len(original_samples)}")
    print(f"  - Augmented samples filtered out: {augmented_count}")

    print(f"Saving original samples to {output_file.name}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(original_samples, f, indent=2, ensure_ascii=False)

    print("Success! Created the unaugmented file.")

if __name__ == "__main__":
    main()
