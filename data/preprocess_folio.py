import json
import sys
from pathlib import Path

# Add project root to sys.path to allow absolute imports of src
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

from src.utils.normalization import normalize_logic_fol_entry, normalize_logic_premise_text

def run_pipeline(input_path: Path, output_path: Path) -> None:
    print(f"Loading folio dataset from: {input_path}")
    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise TypeError("Expected a list in folio-train.json")
    
    processed = []
    for sample in data:
        new_sample = {}
        
        # Preserve core keys and rename/normalize premises
        new_sample["story_id"] = sample.get("story_id")
        new_sample["example_id"] = sample.get("example_id")
        new_sample["conclusion"] = sample.get("conclusion")
        
        # Get premises NL
        premises = sample.get("premises")
        if premises is None:
            # Fallback to premises-NL if already processed
            premises = sample.get("premises-NL", [])
            
        if not isinstance(premises, list):
            raise TypeError("premises must be a list")
            
        # Filter out empty or whitespace-only lines
        premises = [p.strip() for p in premises if p.strip()]
        new_sample["premises-NL"] = [normalize_logic_premise_text(p) for p in premises]
        
        # Normalize premises FOL
        fol_list = sample.get("premises-FOL", [])
        if not isinstance(fol_list, list):
            raise TypeError("premises-FOL must be a list")
            
        # Filter out empty or whitespace-only lines
        fol_list = [p.strip() for p in fol_list if p.strip()]
        new_sample["premises-FOL"] = [normalize_logic_fol_entry(p) for p in fol_list]
        
        new_sample["label"] = sample.get("label")
        new_sample["source"] = sample.get("source")
        
        processed.append(new_sample)
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)
        
    print(f"Processed folio dataset successfully. Output saved to: {output_path}")
    print(f"Total items: {len(processed)}")

if __name__ == "__main__":
    input_path = root / "data" / "folio-train.json"
    output_path = root / "data" / "processed" / "folio-train.json"
    run_pipeline(input_path, output_path)
