import json
import re
from collections import defaultdict, Counter

file_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Group by source
folio_samples = [d for d in data if d.get("dataset_source") == "folio-train"]
logic_based_samples = [d for d in data if d.get("dataset_source") == "logic_based"]

def get_unique_stories(samples):
    seen = set()
    unique = []
    for s in samples:
        prem = tuple(s.get("premises-NL"))
        if prem not in seen:
            seen.add(prem)
            unique.append(s)
    return unique

folio_stories = get_unique_stories(folio_samples)
logic_based_stories = get_unique_stories(logic_based_samples)

print(f"Folio stories: {len(folio_stories)}")
print(f"Logic-based stories: {len(logic_based_stories)}")

# Let's analyze the FOL structure of logic_based stories
# We want to abstract each story's FOL formulas to see if they follow the same template.
# A formula template can be constructed by replacing predicates with placeholders like P1, P2, P3.
def abstract_formulas(fol_list):
    # Extract all unique predicates
    pred_regex = re.compile(r'\b([A-Za-z][A-Za-z0-9_]*)\s*\(')
    excluded = {"ForAll", "Exists", "AND", "OR", "NOT"}
    
    predicates = []
    for fol in fol_list:
        preds = pred_regex.findall(fol)
        for p in preds:
            if p not in excluded and p not in predicates:
                predicates.append(p)
                
    # Create mapping to P0, P1, P2...
    pred_map = {p: f"P{idx}" for idx, p in enumerate(predicates)}
    
    # Also find constants
    # Constants are usually lowercase names in parentheses, e.g. Student(ha) or Specialize(miroslav, renaissance)
    # Let's replace constants too to abstract completely.
    # We can match words inside parentheses that start with a lowercase letter, or are alphanumeric.
    # A simple way is to replace the specific predicate names, and replace variables/constants inside parentheses.
    abstracted = []
    for fol in fol_list:
        s = fol
        # Replace predicates
        # Sort by length descending to avoid partial matches
        for p in sorted(predicates, key=len, reverse=True):
            s = re.sub(r'\b' + p + r'\b', pred_map[p], s)
        # Normalize variables inside, e.g. x, y, z or names like john, sophia
        # Let's replace any word inside P_i(word1, word2) with generic vars.
        # This is a bit complex, but even just replacing predicate names gives a good signature.
        abstracted.append(s)
    return tuple(sorted(abstracted))

# Let's find how many unique logical templates exist in logic_based vs folio-train
logic_based_templates = defaultdict(list)
for s in logic_based_stories:
    tmpl = abstract_formulas(s.get("premises-FOL", []))
    logic_based_templates[tmpl].append(s.get("story_id"))

folio_templates = defaultdict(list)
for s in folio_stories:
    tmpl = abstract_formulas(s.get("premises-FOL", []))
    folio_templates[tmpl].append(s.get("story_id"))

print(f"\n=== Template Analysis ===")
print(f"Logic-based: {len(logic_based_stories)} stories map to {len(logic_based_templates)} unique logical templates.")
print(f"Folio: {len(folio_stories)} stories map to {len(folio_templates)} unique logical templates.")

# Print top templates in logic_based
template_sizes = sorted([(len(ids), tmpl) for tmpl, ids in logic_based_templates.items()], reverse=True)
print("\nTop 5 most frequent logical templates in logic_based:")
for idx, (count, tmpl) in enumerate(template_sizes[:5]):
    print(f"\nTemplate {idx+1} (used by {count} stories):")
    for formula in tmpl[:4]:
        print(f"  - {formula}")
    if len(tmpl) > 4:
        print(f"  - ... ({len(tmpl) - 4} more formulas)")
