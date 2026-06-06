import json
import re
from collections import Counter, defaultdict

file_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Group by story to get statistics per story
stories = defaultdict(list)
for d in data:
    src = d.get("dataset_source")
    premises_key = tuple(p.strip().lower() for p in d.get("premises-NL"))
    stories[(src, premises_key)].append(d)

print(f"Loaded {len(data)} samples across {len(stories)} unique stories.")

# Quantifiers to exclude from predicate lists
EXCLUDED = {"ForAll", "Exists", "AND", "OR", "NOT"}

# Heuristic to detect variables: single letter or bound variable
def get_bound_variables(fol):
    # e.g., ForAll(x, ...) or Exists(y, ...)
    # Let's match (ForAll|Exists)(variable,
    matches = re.findall(r'\b(?:ForAll|Exists)\s*\(\s*([a-zA-Z0-9_]+)\s*,', fol)
    return set(matches)

# Parsed data structures
all_entities = Counter()
all_predicates = Counter()
predicate_arity = defaultdict(set) # predicate -> set of arities
arity_counts = Counter() # arity -> count of occurrences

story_entities = defaultdict(set)
story_predicates = defaultdict(set)

mixed_quant_stories = 0
nested_quant_stories = 0
total_stories = len(stories)

formula_mixed = 0
formula_nested = 0
total_formulas = 0

for story_idx, ((src, premises_key), samples) in enumerate(stories.items()):
    fol_list = samples[0].get("premises-FOL", [])
    
    story_has_mixed = False
    story_has_nested = False
    
    for fol in fol_list:
        total_formulas += 1
        bound_vars = get_bound_variables(fol)
        
        # Check quantifiers for error opportunities
        quants = re.findall(r'\b(ForAll|Exists)\b', fol)
        has_forall = "ForAll" in quants
        has_exists = "Exists" in quants
        
        # Mixed quantifiers: both ForAll and Exists in the same formula
        if has_forall and has_exists:
            formula_mixed += 1
            story_has_mixed = True
            
        # Nested quantifiers: quantifier depth >= 2 (e.g. ForAll(x, ForAll(y, ...)) or ForAll(x, Exists(y, ...)))
        # Consecutive quantifiers in regex
        # E.g., ForAll(x, ForAll(y, ...)) or ForAll(x, Exists(y, ...))
        # Let's count consecutive quantifiers at the beginning, or check if there is nesting
        # We can find if a quantifier is nested inside another quantifier
        # A simple check: if we search for ForAll/Exists, and inside its body there is another ForAll/Exists.
        # We can search for ForAll/Exists followed by another ForAll/Exists before its matching closing paren.
        # Let's write a quick check: if the count of quantifiers in a single formula is >= 2
        # Usually, if a formula has >= 2 quantifiers, they are nested in this dataset.
        if len(quants) >= 2:
            formula_nested += 1
            story_has_nested = True
            
        # Extract predicates and their arguments
        # e.g., Specialize(miroslav, renaissance)
        # We search for Word(args)
        matches = re.finditer(r'\b([A-Za-z][A-Za-z0-9_]*)\s*\((.*?)\)', fol)
        for match in matches:
            pred = match.group(1)
            if pred in EXCLUDED:
                continue
                
            args_str = match.group(2).strip()
            # Split args by comma, ignoring nested commas (if any, though rare here)
            # Since arguments here are simple variables or constants, splitting by comma is safe
            if args_str == "":
                args = []
            else:
                args = [a.strip() for a in args_str.split(",")]
                
            arity = len(args)
            
            all_predicates[pred] += 1
            predicate_arity[pred].add(arity)
            arity_counts[arity] += 1
            story_predicates[story_idx].add(pred)
            
            # Identify constants (entities)
            for arg in args:
                # If the arg is a variable, it is either:
                # 1. in bound_vars
                # 2. is a single character (x, y, z, etc.)
                is_var = arg in bound_vars or (len(arg) == 1 and arg.islower())
                if not is_var:
                    # It's a constant entity
                    all_entities[arg] += 1
                    story_entities[story_idx].add(arg)

    if story_has_mixed:
        mixed_quant_stories += 1
    if story_has_nested:
        nested_quant_stories += 1

print("\n=== Entity Statistics ===")
print(f"Total unique entities (constants) in dataset: {len(all_entities)}")
print(f"Top 15 most common entities:")
for ent, count in all_entities.most_common(15):
    print(f"  - {ent}: {count} occurrences")

entity_counts_per_story = [len(story_entities[i]) for i in range(total_stories)]
print(f"Entities per story stats:")
print(f"  - Min: {min(entity_counts_per_story)}")
print(f"  - Max: {max(entity_counts_per_story)}")
print(f"  - Average: {sum(entity_counts_per_story)/total_stories:.2f}")


print("\n=== Predicate Statistics ===")
print(f"Total unique predicates in dataset: {len(all_predicates)}")
print(f"Top 15 most common predicates:")
for pred, count in all_predicates.most_common(15):
    arities = list(predicate_arity[pred])
    print(f"  - {pred} (arity {arities}): {count} occurrences")

predicate_counts_per_story = [len(story_predicates[i]) for i in range(total_stories)]
print(f"Predicates per story stats:")
print(f"  - Min: {min(predicate_counts_per_story)}")
print(f"  - Max: {max(predicate_counts_per_story)}")
print(f"  - Average: {sum(predicate_counts_per_story)/total_stories:.2f}")

print("\nPredicate Arity Distribution (occurrences in formulas):")
total_occurrences = sum(arity_counts.values())
for arity, count in sorted(arity_counts.items()):
    print(f"  - Arity {arity}: {count} occurrences ({count/total_occurrences*100:.2f}%)")


print("\n=== Quantifier Error Opportunity ===")
print(f"Total formulas: {total_formulas}")
print(f"Formulas with mixed quantifiers (both ForAll & Exists): {formula_mixed} ({formula_mixed/total_formulas*100:.2f}%)")
print(f"Formulas with nested quantifiers (depth >= 2): {formula_nested} ({formula_nested/total_formulas*100:.2f}%)")
print(f"Stories with mixed quantifiers: {mixed_quant_stories} / {total_stories} ({mixed_quant_stories/total_stories*100:.2f}%)")
print(f"Stories with nested quantifiers: {nested_quant_stories} / {total_stories} ({nested_quant_stories/total_stories*100:.2f}%)")
