import json
import os
import re
from collections import Counter, defaultdict

file_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total samples: {len(data)}")

# 1. Dataset overview by source
sources = Counter(d.get("dataset_source") for d in data)
print("\n=== Dataset Sources ===")
for source, count in sources.items():
    print(f"Source: {source}, Samples: {count}")

# 2. Stories and dataset size by story
# We define a story uniquely by its dataset_source and premises-NL content (standardized)
def standardize_premises(premises):
    return tuple(p.strip().lower() for p in premises)

stories = defaultdict(list)
for i, d in enumerate(data):
    src = d.get("dataset_source")
    premises_key = standardize_premises(d.get("premises-NL"))
    stories[(src, premises_key)].append(d)

print(f"\n=== Stories Distribution ===")
print(f"Total unique stories: {len(stories)}")
stories_by_source = defaultdict(int)
for (src, _), samples in stories.items():
    stories_by_source[src] += 1

for src, count in stories_by_source.items():
    print(f"  - {src}: {count} unique stories")

# Questions per story statistics
q_counts = [len(samples) for samples in stories.values()]
print(f"Questions per story stats:")
print(f"  - Min: {min(q_counts)}")
print(f"  - Max: {max(q_counts)}")
print(f"  - Mean: {sum(q_counts)/len(q_counts):.2f}")
print(f"  - Median: {sorted(q_counts)[len(q_counts)//2]}")

# 3. Logic phenomena distribution
# Connectives and quantifiers in FOL premises
connectives = Counter()
quantifiers = Counter()
formula_types = Counter() # Propositional vs First-Order Logic
premise_counts = []
total_premises = 0

for (src, premises_key), samples in stories.items():
    # We look at premises of the story (to avoid double counting same story premises)
    first_sample = samples[0]
    fol_list = first_sample.get("premises-FOL", [])
    premise_counts.append(len(fol_list))
    total_premises += len(fol_list)
    
    story_has_quantifier = False
    for fol in fol_list:
        # Check quantifiers
        has_forall = "ForAll" in fol
        has_exists = "Exists" in fol
        if has_forall:
            quantifiers["ForAll"] += 1
            story_has_quantifier = True
        if has_exists:
            quantifiers["Exists"] += 1
            story_has_quantifier = True
        
        # Check connectives
        # Avoid matching substrings like 'AND' in predicates if any, but FOL should be normalized
        # We can use regex to find uppercase connectives: AND, OR, NOT, ->, <->
        ops = re.findall(r'\b(AND|OR|NOT)\b|->|<->', fol)
        for op_group in ops:
            # op_group is a tuple if there are multiple groups, let's normalize
            op = "".join(op_group)
            if op:
                connectives[op] += 1
            else:
                # implies or equiv
                if "->" in fol:
                    connectives["->"] += fol.count("->")
                if "<->" in fol:
                    connectives["<->"] += fol.count("<->")
        # Ensure count is accurate by doing direct substring counts for operators
        # but be careful with word boundaries
    if story_has_quantifier:
        formula_types["First-Order Logic (FOL)"] += 1
    else:
        formula_types["Propositional Logic"] += 1

print("\n=== Logic Phenomena (Unique Stories) ===")
print(f"Total premises: {total_premises}")
print(f"Average premises per story: {total_premises / len(stories):.2f}")
print("Logic systems distribution across stories:")
for l_type, count in formula_types.items():
    print(f"  - {l_type}: {count} stories ({count/len(stories)*100:.2f}%)")

print("Connectives in premises:")
# Re-count connectives carefully to ensure accuracy
conn_counts = {"AND": 0, "OR": 0, "NOT": 0, "->": 0, "<->": 0}
for (src, _), samples in stories.items():
    for fol in samples[0].get("premises-FOL", []):
        conn_counts["AND"] += len(re.findall(r'\bAND\b', fol))
        conn_counts["OR"] += len(re.findall(r'\bOR\b', fol))
        conn_counts["NOT"] += len(re.findall(r'\bNOT\b', fol))
        conn_counts["->"] += fol.count("->")
        conn_counts["<->"] += fol.count("<->")

for conn, count in conn_counts.items():
    print(f"  - {conn}: {count} occurrences")

print("Quantifiers in premises:")
quant_counts = {"ForAll": 0, "Exists": 0}
for (src, _), samples in stories.items():
    for fol in samples[0].get("premises-FOL", []):
        quant_counts["ForAll"] += fol.count("ForAll")
        quant_counts["Exists"] += fol.count("Exists")
for q, count in quant_counts.items():
    print(f"  - {q}: {count} occurrences")

# 4. Duplication and Overlap
print("\n=== Duplication & Overlap ===")
# Exact duplicate samples (premises + question + answer)
dup_samples = defaultdict(list)
for i, d in enumerate(data):
    key = (d.get("dataset_source"), standardize_premises(d.get("premises-NL")), d.get("question").strip().lower(), str(d.get("answer")).strip())
    dup_samples[key].append(i)

dup_count = sum(len(indices) - 1 for indices in dup_samples.values() if len(indices) > 1)
print(f"Exact duplicate samples (same story + question + answer): {dup_count}")

# Check story overlap between folio-train and logic_based
folio_stories = set(standardize_premises(s.get("premises-NL")) for s in data if s.get("dataset_source") == "folio-train")
logic_stories = set(standardize_premises(s.get("premises-NL")) for s in data if s.get("dataset_source") == "logic_based")
overlap_stories = folio_stories.intersection(logic_stories)
print(f"Stories overlapping between folio-train and logic_based: {len(overlap_stories)}")

# 5. Output structure
print("\n=== Output Structure ===")
# MCQ vs Statement questions
mcq_samples = []
statement_samples = []
for d in data:
    q = d.get("question", "")
    ans = d.get("answer", "")
    # Check if A/B/C/D is the answer or if there are options A., B., C., D. in question
    if ans in ["A", "B", "C", "D"] or re.search(r'\b[A-D][\.\)]', q):
        mcq_samples.append(d)
    else:
        statement_samples.append(d)

print(f"MCQ questions: {len(mcq_samples)}")
mcq_ans_dist = Counter(d.get("answer") for d in mcq_samples)
print("MCQ Answer Distribution:", dict(mcq_ans_dist))

print(f"Statement questions: {len(statement_samples)}")
stmt_ans_dist = Counter(d.get("answer") for d in statement_samples)
print("Statement Answer Distribution:", dict(stmt_ans_dist))

# 6. Template vs Human Analysis
# Let's write a heuristic to detect if stories are synthetically generated from templates
# Template stories often have the exact same sentence structure but different noun variables.
# E.g., "If x is a Y, then x is a Z."
# Let's standardize the text of each story by replacing capitalized nouns with a placeholder and see how many collapse.
def abstract_story(premises):
    abstracted = []
    for p in premises:
        # Lowercase everything except capital words that represent entities
        # and replace specific names or nouns with generic placeholders
        p_sub = p
        # Replace common names or capitalized terms with placeholders
        # We can find all capitalized words (except at the start of a sentence)
        # Or let's just use a simpler heuristic: how similar are the sentence lists between stories?
        # Let's count Jaccard similarity or Levenshtein distance, or count stories that are structurally identical.
        # Let's look at template structures in logic_based.
        pass
    return abstracted

# Let's print out some unique stories from logic_based to see if they are templates
print("\n=== Inspecting logic_based for template patterns ===")
for i, ((src, premises_key), samples) in enumerate(stories.items()):
    if src == "logic_based" and i < 15:
        print(f"Story {i} (Story ID: {samples[0].get('story_id')}, Samples count: {len(samples)}):")
        print(f"  First premise: {samples[0].get('premises-NL')[0]}")
        print(f"  Second premise: {samples[0].get('premises-NL')[1] if len(samples[0].get('premises-NL')) > 1 else 'N/A'}")
