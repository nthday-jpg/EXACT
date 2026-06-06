import json
import re

file_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Analyze word counts
premise_words = []
question_words = []

for d in data:
    for p in d.get("premises-NL", []):
        premise_words.append(len(p.split()))
    question_words.append(len(d.get("question", "").split()))

print(f"NL Premise word count stats:")
print(f"  - Min: {min(premise_words)}")
print(f"  - Max: {max(premise_words)}")
print(f"  - Average: {sum(premise_words)/len(premise_words):.2f}")

print(f"NL Question word count stats:")
print(f"  - Min: {min(question_words)}")
print(f"  - Max: {max(question_words)}")
print(f"  - Average: {sum(question_words)/len(question_words):.2f}")

# Quantifier nesting depth analysis
# We count how many nested ForAll/Exists are in each formula
def get_nesting_depth(fol):
    # Match ForAll(x, ForAll(y, ...)) or Exists(x, Exists(y, ...))
    # Let's count consecutive ForAll or Exists prefixes.
    # E.g. ForAll(x, ForAll(y, ForAll(z, ...)))
    # A simple regex to find nesting is to search for sequences of (ForAll|Exists)\([a-z],\s*
    # Let's do a simple count of how many quantifiers are in the formula
    quantifiers_in_formula = len(re.findall(r'\b(ForAll|Exists)\b', fol))
    return quantifiers_in_formula

max_depth = 0
all_depths = []
for d in data:
    for fol in d.get("premises-FOL", []):
        depth = get_nesting_depth(fol)
        all_depths.append(depth)
        if depth > max_depth:
            max_depth = depth

print(f"\nFOL Quantifiers per formula stats:")
print(f"  - Max quantifiers in a single formula: {max_depth}")
print(f"  - Average quantifiers per formula: {sum(all_depths)/len(all_depths):.2f}")
# Count frequencies of quantifiers count
depth_counts = {}
for dep in all_depths:
    depth_counts[dep] = depth_counts.get(dep, 0) + 1
print("Quantifiers count frequency:")
for dep, count in sorted(depth_counts.items()):
    print(f"  - {dep} quantifiers: {count} formulas ({count/len(all_depths)*100:.2f}%)")
