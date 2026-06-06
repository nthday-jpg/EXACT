import json
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict

file_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid.json"
raw_logic_based_path = r"d:\mduy\source\repos\EXACT\data\logic_based.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. Quantifier Pattern Distribution
print("=== 1. Quantifier Pattern Distribution ===")
quantifier_patterns = Counter()
total_formulas = 0

for d in data:
    for fol in d.get("premises-FOL", []):
        total_formulas += 1
        # Find all quantifiers in order of appearance
        quants = re.findall(r'\b(ForAll|Exists)\b', fol)
        if not quants:
            pattern = "None (Propositional)"
        else:
            pattern = " ".join(quants)
        quantifier_patterns[pattern] += 1

for pat, count in sorted(quantifier_patterns.items(), key=lambda x: x[1], reverse=True):
    print(f"  - {pat}: {count} formulas ({count/total_formulas*100:.2f}%)")


# 2. Negation Position Analysis
print("\n=== 2. Negation Position Analysis ===")
negation_types = Counter()
total_nots = 0

# Helper to classify each NOT
# We look at what follows 'NOT '
for d in data:
    for fol in d.get("premises-FOL", []):
        # Find all occurrences of NOT
        # To find positions, we can use finditer
        for match in re.finditer(r'\bNOT\b', fol):
            total_nots += 1
            idx = match.end()
            # Get the remaining string after 'NOT'
            remaining = fol[idx:].strip()
            
            if remaining.startswith("ForAll") or remaining.startswith("Exists"):
                negation_types["Quantifier-level Negation (e.g. NOT ForAll)"] += 1
            elif remaining.startswith("("):
                # Check if it's a nested predicate or compound expression
                # Let's count how many binary connectives (AND, OR, ->, <->) are inside the outer parenthesis.
                # A simple heuristic is: if there are connectives inside the parenthesis, it's compound.
                # Let's find the matching closing parenthesis
                depth = 0
                paren_content = ""
                for char in remaining[1:]:
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        if depth == 0:
                            break
                        depth -= 1
                    paren_content += char
                
                # Check for binary operators in paren_content
                if any(op in paren_content for op in ["AND", "OR", "->", "<->"]):
                    negation_types["Compound-level Negation (e.g. NOT (A AND B))"] += 1
                else:
                    # e.g., NOT (P(x)) is still a predicate-level negation
                    negation_types["Predicate-level Negation (Literal)"] += 1
            else:
                # e.g., NOT P(x)
                negation_types["Predicate-level Negation (Literal)"] += 1

for neg_type, count in negation_types.items():
    print(f"  - {neg_type}: {count} occurrences ({count/total_nots*100:.2f}%)")


# 3. Reasoning Depth Analysis
print("\n=== 3. Reasoning Depth Analysis ===")

# (A) Analyze the raw idx field from logic_based.json (which lists the exact premises needed per question)
print("Analyzing 'idx' field (number of premises required per question) in logic_based.json:")
try:
    with open(raw_logic_based_path, 'r', encoding='utf-8') as f:
        raw_logic = json.load(f)
    idx_lengths = []
    for record in raw_logic:
        idx_list = record.get("idx", [])
        for item in idx_list:
            # item is a list of premise indices, e.g. [1, 2, 4]
            if isinstance(item, list):
                idx_lengths.append(len(item))
    idx_counter = Counter(idx_lengths)
    print("  Required premises per question in logic_based:")
    for num_prems, freq in sorted(idx_counter.items()):
        print(f"    - {num_prems} premises required: {freq} questions ({freq/len(idx_lengths)*100:.2f}%)")
    print(f"    - Mean reasoning depth (premises count): {sum(idx_lengths)/len(idx_lengths):.2f}")
except Exception as e:
    print(f"  Could not analyze raw idx: {e}")

# (B) Analyze Logical Implication Depth (Longest path in predicate dependency graph per story)
print("\nAnalyzing Logical Implication Depth (longest implication path in predicate dependency graph):")

def extract_predicates(text):
    pred_regex = re.compile(r'\b([A-Za-z][A-Za-z0-9_]*)\s*\(', re.UNICODE)
    excluded = {"ForAll", "Exists", "AND", "OR", "NOT"}
    return set(p for p in pred_regex.findall(text) if p not in excluded)

def get_longest_path(graph):
    # Find longest path in a directed graph using DFS with memoization
    memo = {}
    
    def dfs(node, visited_in_path):
        if node in memo:
            return memo[node]
        if node in visited_in_path:
            return 0  # Cycle detected, break path to prevent infinite loop
        
        visited_in_path.add(node)
        max_dist = 0
        neighbors = graph.get(node, set())
        for neighbor in neighbors:
            dist = 1 + dfs(neighbor, visited_in_path)
            if dist > max_dist:
                max_dist = dist
        visited_in_path.remove(node)
        
        memo[node] = max_dist
        return max_dist

    max_overall = 0
    # Iterate over a copy of keys to prevent RuntimeError
    for node in list(graph.keys()):
        dist = dfs(node, set())
        if dist > max_overall:
            max_overall = dist
    return max_overall

# Group by unique story first to compute logic depth per story
stories = defaultdict(list)
for d in data:
    src = d.get("dataset_source")
    premises_key = tuple(p.strip().lower() for p in d.get("premises-NL"))
    stories[(src, premises_key)].append(d)

source_depths = defaultdict(list)
for (src, _), samples in stories.items():
    first_sample = samples[0]
    fol_list = first_sample.get("premises-FOL", [])
    
    # Build dependency graph
    graph = defaultdict(set)
    for fol in fol_list:
        if "->" in fol:
            # Split by implication
            parts = fol.split("->")
            if len(parts) == 2:
                antecedent, consequent = parts[0], parts[1]
                preds_ant = extract_predicates(antecedent)
                preds_con = extract_predicates(consequent)
                for u in preds_ant:
                    for v in preds_con:
                        if u != v:
                            graph[u].add(v)
                            
    depth = get_longest_path(graph)
    source_depths[src].append(depth)

for src, depths in source_depths.items():
    depth_counter = Counter(depths)
    print(f"  Source: {src} (Total stories: {len(depths)}):")
    for dep, count in sorted(depth_counter.items()):
        print(f"    - Implication depth {dep}: {count} stories ({count/len(depths)*100:.2f}%)")
    print(f"    - Mean implication depth: {sum(depths)/len(depths):.2f}")
