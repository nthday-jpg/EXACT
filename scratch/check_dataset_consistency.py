import json
from pathlib import Path

root_dir = Path(__file__).resolve().parents[1]
data_path = root_dir / "data" / "logic_based.json"

with open(data_path, "r", encoding="utf-8") as f:
    dataset = json.load(f)

print("=" * 70)
print("INSPECTING DATASET GROUND TRUTH LABELS & EXPLANATIONS")
print("=" * 70)

for idx in range(15):
    sample = dataset[idx]
    premises_nl = sample.get("premises-NL", [])
    questions = sample.get("questions", [])
    answers = sample.get("answers", [])
    explanations = sample.get("explanation", [])
    
    # We are interested in Yes/No questions (usually the second question in each sample)
    if len(questions) >= 2:
        q_nl = questions[1]
        ans = answers[1]
        exp = explanations[1] if len(explanations) >= 2 else "No explanation provided"
        
        print(f"\nSample {idx} (Question 1):")
        print(f"  Question NL: {q_nl}")
        print(f"  GT Answer  : {ans}")
        print(f"  Explanation: {exp}")
        
        # Check if explanation supports "Yes" but answer is "No"
        exp_lower = exp.lower()
        if ans == "No" and ("satisfying all conditions" in exp_lower or "so john can" in exp_lower or "so he meets the requirements" in exp_lower or "entails" in exp_lower or "the reasoning is valid and consistent" in exp_lower or "supports the statement" in exp_lower):
            print("  >>> DANGER: Ground truth answer is 'No' but explanation says it is logically entailed (should be 'Yes')!")
        elif ans == "Yes" and ("failing the" in exp_lower or "does not meet" in exp_lower or "lacks" in exp_lower or "prevents" in exp_lower):
            print("  >>> DANGER: Ground truth answer is 'Yes' but explanation says it is NOT logically entailed (should be 'No')!")
            
print("=" * 70)
