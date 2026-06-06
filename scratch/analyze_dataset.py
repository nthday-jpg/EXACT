import json
import re
import math
from collections import Counter, defaultdict
import itertools

# Regex for tokenizing FOL formulas
TOKEN_RE = re.compile(
    r"\s*(->|<->|AND|OR|NOT|IN|ForAll|Exists|>=|<=|!=|=|>|<|\(|\)|,|\+|-|\d+\.\d+|\d+|'[^']*'|[^\W\d][\w-]*)"
)

KEYWORDS = {"ForAll", "Exists", "AND", "OR", "NOT", "IN"}

# AST Node for FOL Parsing
class Node:
    def __init__(self, op, children=None, value=None):
        self.op = op
        self.children = children or []
        self.value = value

    def __repr__(self):
        if self.value is not None:
            return f"{self.op}({self.value})"
        return f"{self.op}({', '.join(map(str, self.children))})"

def parse_formula(formula_str):
    tokens = [t for t in TOKEN_RE.findall(formula_str) if t.strip()]
    idx = 0
    
    def peek():
        return tokens[idx] if idx < len(tokens) else None
        
    def next_token():
        nonlocal idx
        tok = peek()
        idx += 1
        return tok
        
    def expect(tok):
        t = next_token()
        if t != tok:
            raise ValueError(f"Expected {tok}, got {t}")
            
    def parse_expr():
        return parse_impl()
        
    def parse_impl():
        left = parse_or()
        tok = peek()
        if tok == "->":
            next_token()
            right = parse_impl()
            return Node("IMPLIES", [left, right])
        elif tok == "<->":
            next_token()
            right = parse_impl()
            return Node("BICOND", [left, right])
        return left
        
    def parse_or():
        left = parse_and()
        while peek() == "OR":
            next_token()
            right = parse_and()
            left = Node("OR", [left, right])
        return left
        
    def parse_and():
        left = parse_not()
        while peek() == "AND":
            next_token()
            right = parse_not()
            left = Node("AND", [left, right])
        return left
        
    def parse_not():
        if peek() == "NOT":
            next_token()
            return Node("NOT", [parse_not()])
        return parse_atom()
        
    def parse_atom():
        tok = peek()
        if tok is None:
            return Node("EMPTY")
        if tok == "(":
            next_token()
            expr = parse_expr()
            expect(")")
            return expr
        elif tok in ("ForAll", "Exists"):
            quant = next_token()
            expect("(")
            var = next_token()
            expect(",")
            body = parse_expr()
            expect(")")
            return Node(quant, [Node("VAR", value=var), body])
        else:
            name = next_token()
            if peek() == "(":
                next_token()
                args = []
                if peek() != ")":
                    while True:
                        args.append(parse_term())
                        if peek() == ",":
                            next_token()
                            continue
                        break
                expect(")")
                return Node("PRED", [Node("NAME", value=name)] + args)
            else:
                return Node("TERM", value=name)
                
    def parse_term():
        name = next_token()
        if peek() == "(":
            next_token()
            args = []
            if peek() != ")":
                while True:
                    args.append(parse_term())
                    if peek() == ",":
                        next_token()
                        continue
                    break
            expect(")")
            return Node("FUNC", [Node("NAME", value=name)] + args)
        return Node("TERM", value=name)

    try:
        return parse_expr()
    except Exception as e:
        return Node("RAW", value=formula_str)

def get_predicates_in_tree(node):
    if node.op == "PRED":
        return {node.children[0].value}
    preds = set()
    for child in node.children:
        preds.update(get_predicates_in_tree(child))
    return preds

def extract_variables_and_entities(formula_str):
    tokens = [t for t in TOKEN_RE.findall(formula_str) if t.strip()]
    bound_vars = set()
    for i in range(len(tokens) - 2):
        if tokens[i] in ("ForAll", "Exists") and tokens[i+1] == "(":
            bound_vars.add(tokens[i+2])
            
    predicates = set()
    entities = set()
    variables = set()
    operators = []
    quant_seq = []
    
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in ("ForAll", "Exists"):
            quant_seq.append(tok)
            operators.append(tok)
        elif tok in ("->", "<->", "AND", "OR", "NOT", "IN", "=", "!=", ">=", "<=", ">", "<"):
            operators.append(tok)
        elif i + 1 < n and tokens[i+1] == "(" and tok.isidentifier() and tok not in KEYWORDS:
            predicates.add(tok)
        elif tok.isidentifier() and tok not in KEYWORDS:
            if tok in bound_vars or tok in ('x', 'y', 'z', 'w', 'v', 'u'):
                variables.add(tok)
            else:
                entities.add(tok)
        i += 1
    return predicates, entities, variables, operators, quant_seq

def standardize_fol(formula_str):
    tokens = [t for t in TOKEN_RE.findall(formula_str) if t.strip()]
    bound_vars = []
    for i in range(len(tokens) - 2):
        if tokens[i] in ("ForAll", "Exists") and tokens[i+1] == "(":
            v = tokens[i+2]
            if v not in bound_vars:
                bound_vars.append(v)
                
    var_map = {v: f"v{idx+1}" for idx, v in enumerate(bound_vars)}
    
    pred_map = {}
    entity_map = {}
    
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in KEYWORDS:
            i += 1
            continue
        if i + 1 < n and tokens[i+1] == "(" and tok.isidentifier():
            if tok not in pred_map:
                pred_map[tok] = f"P{len(pred_map)+1}"
            i += 1
            continue
        if tok.isidentifier() and tok not in var_map:
            if tok in ('x', 'y', 'z', 'w', 'v', 'u'):
                var_map[tok] = tok
            else:
                if tok not in entity_map:
                    entity_map[tok] = f"c{len(entity_map)+1}"
        i += 1
        
    new_tokens = []
    i = 0
    while i < n:
        tok = tokens[i]
        if tok in KEYWORDS:
            new_tokens.append(tok)
        elif i + 1 < n and tokens[i+1] == "(" and tok.isidentifier():
            new_tokens.append(pred_map[tok])
        elif tok.isidentifier():
            if tok in var_map:
                new_tokens.append(var_map[tok])
            elif tok in entity_map:
                new_tokens.append(entity_map[tok])
            else:
                new_tokens.append(tok)
        else:
            new_tokens.append(tok)
        i += 1
        
    res = []
    for idx, tok in enumerate(new_tokens):
        if tok in ("(", ")", ",", "+", "-"):
            res.append(tok)
        elif tok in ("->", "<->", "AND", "OR", "NOT", "IN", "=", "!=", ">=", "<=", ">", "<"):
            res.append(f" {tok} ")
        else:
            if idx + 1 < len(new_tokens) and new_tokens[idx+1] in ("(", ",", ")"):
                res.append(tok)
            else:
                res.append(tok + " ")
                
    standardized = "".join(res).strip()
    standardized = re.sub(r'\s+', ' ', standardized)
    standardized = re.sub(r'\s+([(),])', r'\1', standardized)
    standardized = re.sub(r'\(\s+', '(', standardized)
    return standardized

def get_implication_edges(node):
    # Find all implies in the node and return left_preds, right_preds
    edges = []
    if node.op == "IMPLIES":
        left_preds = get_predicates_in_tree(node.children[0])
        right_preds = get_predicates_in_tree(node.children[1])
        for u in left_preds:
            for v in right_preds:
                edges.append((u, v))
    for child in node.children:
        edges.extend(get_implication_edges(child))
    return edges

def max_quantifier_nesting(node):
    if node.op in ("ForAll", "Exists"):
        return 1 + max_quantifier_nesting(node.children[1])
    if not node.children:
        return 0
    return max([max_quantifier_nesting(c) for c in node.children], default=0)

def count_connectives(node):
    count = 0
    if node.op in ("AND", "OR", "NOT", "IMPLIES", "BICOND"):
        count = 1
    return count + sum(count_connectives(c) for c in node.children)

def longest_acyclic_path_len(graph):
    memo = {}
    def dfs(node, visited):
        if node in memo:
            return memo[node]
        max_len = 0
        visited.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                max_len = max(max_len, 1 + dfs(neighbor, visited))
        visited.remove(node)
        return max_len

    overall_max = 0
    for node in graph:
        overall_max = max(overall_max, dfs(node, set()))
    return overall_max

def tokenize_nl(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    return [w for w in text.split() if w]

def calculate_entropy(counts_dict):
    total = sum(counts_dict.values())
    if total == 0:
        return 0.0
    entropy = 0.0
    for val in counts_dict.values():
        p = val / total
        entropy -= p * math.log2(p)
    return entropy

def main():
    print("Loading dataset...")
    with open('data/processed/logic_merged_valid.json', 'r', encoding='utf-8') as f:
        dataset = json.load(f)
        
    print(f"Loaded {len(dataset)} samples.")
    
    # Storage for results
    nl_tokens_all = []
    predicates_all = Counter()
    entities_all = Counter()
    
    # 1. Vocab & Entities
    story_ids = set()
    stories_map = defaultdict(list)
    
    # Maps for checking entity-story span
    entity_stories = defaultdict(set)
    predicate_stories = defaultdict(set)
    
    # Standardized logical structures
    logical_structures = Counter()
    
    # Quantifiers
    quant_counts = Counter()
    quant_transitions = Counter()
    
    # Graph and reasoning complexity stats
    graph_depths = []
    graph_branching_factors = []
    premise_counts = []
    connective_complexities = []
    quantifier_nestings = []
    
    # Connectives coverage
    operators_counts = Counter()
    operators_per_formula = []
    
    # Answers
    answers_dist = Counter()
    
    parsed_examples = []
    
    for idx, item in enumerate(dataset):
        story_id = item.get("story_id", idx)
        story_ids.add(story_id)
        stories_map[story_id].append(idx)
        
        premises_nl = item.get("premises-NL", [])
        premises_fol = item.get("premises-FOL", [])
        question = item.get("question", "")
        answer = item.get("answer", "Unknown")
        answers_dist[answer] += 1
        
        # Tokenize NL
        nl_text = " ".join(premises_nl) + " " + question
        nl_tokens = tokenize_nl(nl_text)
        nl_tokens_all.extend(nl_tokens)
        
        # Parse FOL formulas
        ex_predicates = set()
        ex_entities = set()
        ex_operators = []
        ex_quant_seq = []
        
        standardized_formulas = []
        
        # Build dependency graph for this example
        dep_graph = defaultdict(set)
        
        ex_quant_nesting = 0
        ex_connective_comp = 0
        
        for fol_str in premises_fol:
            preds, ents, vars_fol, ops, qseq = extract_variables_and_entities(fol_str)
            
            ex_predicates.update(preds)
            ex_entities.update(ents)
            ex_operators.extend(ops)
            ex_quant_seq.extend(qseq)
            
            # Map predicates/entities to stories
            for p in preds:
                predicate_stories[p].add(story_id)
            for e in ents:
                entity_stories[e].add(story_id)
                
            # Parse formula tree
            tree = parse_formula(fol_str)
            ex_quant_nesting = max(ex_quant_nesting, max_quantifier_nesting(tree))
            ex_connective_comp += count_connectives(tree)
            
            # Extract implication edges
            edges = get_implication_edges(tree)
            for u, v in edges:
                dep_graph[u].add(v)
                
            standardized_formulas.append(standardize_fol(fol_str))
            
        # Standardized structure of this example
        # Sort standardized formulas so order doesn't affect identical structures
        std_struct = " ; ".join(sorted(standardized_formulas))
        logical_structures[std_struct] += 1
        
        # Quantifier transitions within this example's formulas
        for fol_str in premises_fol:
            _, _, _, _, qseq = extract_variables_and_entities(fol_str)
            for q1, q2 in zip(qseq, qseq[1:]):
                quant_transitions[f"{q1} -> {q2}"] += 1
            for q in qseq:
                quant_counts[q] += 1
                
        # Reasoning metrics
        depth = longest_acyclic_path_len(dep_graph)
        graph_depths.append(depth)
        
        # Branching factor: avg out-degree of non-sink nodes
        non_sinks = [n for n in dep_graph if len(dep_graph[n]) > 0]
        if non_sinks:
            bf = sum(len(dep_graph[n]) for n in non_sinks) / len(non_sinks)
        else:
            bf = 0.0
        graph_branching_factors.append(bf)
        
        premise_counts.append(len(premises_fol))
        connective_complexities.append(ex_connective_comp)
        quantifier_nestings.append(ex_quant_nesting)
        
        for op in ex_operators:
            operators_counts[op] += 1
            
        predicates_all.update(ex_predicates)
        entities_all.update(ex_entities)
        
        parsed_examples.append({
            "idx": idx,
            "nl_tokens": set(nl_tokens),
            "std_struct": std_struct,
            "story_id": story_id,
            "depth": depth,
            "quant_nesting": ex_quant_nesting,
            "connective_complexity": ex_connective_comp,
            "premise_count": len(premises_fol)
        })

    # Vocabulary statistics
    nl_counter = Counter(nl_tokens_all)
    total_nl_tokens = len(nl_tokens_all)
    unique_nl_tokens = len(nl_counter)
    
    # Good-Turing OOV Risk Estimation: N1 / N
    nl_n1 = sum(1 for w, c in nl_counter.items() if c == 1)
    nl_oov_risk = nl_n1 / total_nl_tokens if total_nl_tokens > 0 else 0
    
    pred_total = sum(predicates_all.values())
    pred_unique = len(predicates_all)
    pred_n1 = sum(1 for w, c in predicates_all.items() if c == 1)
    pred_oov_risk = pred_n1 / pred_total if pred_total > 0 else 0
    
    ent_total = sum(entities_all.values())
    ent_unique = len(entities_all)
    ent_n1 = sum(1 for w, c in entities_all.items() if c == 1)
    ent_oov_risk = ent_n1 / ent_total if ent_total > 0 else 0
    
    # Cumulative frequency of top tokens to check memorization/dependency
    nl_sorted = sorted(nl_counter.values(), reverse=True)
    nl_top_10pct_sum = sum(nl_sorted[:int(len(nl_sorted)*0.1)])
    nl_dep_ratio = nl_top_10pct_sum / total_nl_tokens if total_nl_tokens > 0 else 0

    # Entity Analysis
    top_50_entities = entities_all.most_common(50)
    # Entity repetition rate: fraction of entities appearing in more than 1 story
    repeated_entities_count = sum(1 for e, stories in entity_stories.items() if len(stories) > 1)
    ent_repetition_rate = repeated_entities_count / ent_unique if ent_unique > 0 else 0
    # Average story span
    avg_ent_story_span = sum(len(stories) for stories in entity_stories.values()) / ent_unique if ent_unique > 0 else 0

    # Predicate Analysis
    pred_entropy = calculate_entropy(predicates_all)
    # Predicate repetition rate & co-occurrence
    # Construct co-occurrence matrix (for top 30 predicates for reporting simplicity, or count total pairs)
    co_occurrences = Counter()
    for idx, item in enumerate(dataset):
        preds_in_ex, _, _, _, _ = extract_variables_and_entities(" ".join(item.get("premises-FOL", [])))
        for p1, p2 in itertools.combinations(sorted(preds_in_ex), 2):
            co_occurrences[(p1, p2)] += 1
            
    # Logical Structure Diversity
    total_structures = len(logical_structures)
    top_structures = logical_structures.most_common(10)
    # Structure distribution: count of structures with frequency 1, 2-5, 6-10, 11+
    struct_freq_bins = Counter()
    for s, c in logical_structures.items():
        if c == 1: struct_freq_bins["1"] += 1
        elif c <= 5: struct_freq_bins["2-5"] += 1
        elif c <= 10: struct_freq_bins["6-10"] += 1
        else: struct_freq_bins["11+"] += 1

    # Quantifiers
    quant_entropy = calculate_entropy(quant_counts)
    
    # Pairwise Similarity & Duplicate Clusters
    # We can optimize pairwise Jaccard:
    print("Computing Jaccard similarities...")
    nl_sets = [ex["nl_tokens"] for ex in parsed_examples]
    std_structs = [ex["std_struct"] for ex in parsed_examples]
    
    nl_duplicates = 0
    fol_duplicates = 0
    both_duplicates = 0
    
    # Duplicate clusters based on identical standardized FOL and high Jaccard NL
    # Let's count pairs with Jaccard NL > 0.9 and Jaccard FOL = 1.0 (identical abstract logic)
    # Since N=1812, we can do full loop
    n_samples = len(parsed_examples)
    high_sim_pairs = 0
    exact_logic_pairs = 0
    
    for i in range(n_samples):
        for j in range(i + 1, n_samples):
            # FOL identity
            if std_structs[i] == std_structs[j]:
                exact_logic_pairs += 1
                
            # NL Jaccard
            set_i = nl_sets[i]
            set_j = nl_sets[j]
            union_len = len(set_i.union(set_j))
            if union_len > 0:
                jaccard_nl = len(set_i.intersection(set_j)) / union_len
            else:
                jaccard_nl = 0
                
            if jaccard_nl > 0.9:
                high_sim_pairs += 1
                if std_structs[i] == std_structs[j]:
                    both_duplicates += 1
                    
    # Effective Dataset Size:
    # Let's cluster examples that share the same story_id (which means they share the same story premises).
    # Grouping by story_id gives the number of unique reasoning scenarios.
    unique_stories_count = len(story_ids)

    # Difficulty Distribution
    difficulty_counts = Counter()
    difficulty_details = defaultdict(list)
    for ex in parsed_examples:
        D = ex["depth"]
        Q = ex["quant_nesting"]
        C = ex["connective_complexity"]
        P = ex["premise_count"]
        
        # Difficulty Heuristic
        if D <= 1 and Q == 0 and C <= 4 and P <= 3:
            diff = "Easy"
        elif D >= 3 or Q >= 2 or C >= 12 or P >= 6:
            diff = "Very Hard"
        elif D >= 2 or Q >= 1 or C >= 8 or P >= 5:
            diff = "Hard"
        else:
            diff = "Medium"
            
        difficulty_counts[diff] += 1
        difficulty_details[diff].append(ex)

    # Operators coverage
    total_formulas = sum(len(item.get("premises-FOL", [])) for item in dataset)
    operators_coverage = {}
    for op in ["ForAll", "Exists", "NOT", "AND", "OR", "->", "<->"]:
        # Count occurrences
        count = operators_counts[op]
        # Percent of examples containing this operator
        ex_count = 0
        for item in dataset:
            has_op = False
            for fol_str in item.get("premises-FOL", []):
                if op in fol_str:
                    has_op = True
                    break
            if has_op:
                ex_count += 1
        operators_coverage[op] = {
            "total_count": count,
            "example_pct": ex_count / len(dataset) if len(dataset) > 0 else 0
        }

    # Write output to JSON
    metrics = {
        "dataset_size": len(dataset),
        "unique_story_ids": unique_stories_count,
        "avg_examples_per_story": len(dataset) / unique_stories_count if unique_stories_count > 0 else 0,
        "answers_distribution": dict(answers_dist),
        "vocabulary": {
            "total_nl_tokens": total_nl_tokens,
            "unique_nl_tokens": unique_nl_tokens,
            "nl_oov_risk": nl_oov_risk,
            "nl_top_10pct_cum_frequency": nl_dep_ratio,
            "unique_predicates": pred_unique,
            "predicates_oov_risk": pred_oov_risk,
            "unique_entities": ent_unique,
            "entities_oov_risk": ent_oov_risk
        },
        "entities": {
            "total_entities_count": ent_total,
            "unique_entities_count": ent_unique,
            "repetition_rate": ent_repetition_rate,
            "avg_story_span": avg_ent_story_span,
            "top_50": [(e, c) for e, c in top_50_entities]
        },
        "predicates": {
            "total_predicates_count": pred_total,
            "unique_predicates_count": pred_unique,
            "entropy": pred_entropy,
            "top_20_cooccurring": [([p1, p2], c) for (p1, p2), c in co_occurrences.most_common(20)]
        },
        "logical_structures": {
            "unique_structures_count": total_structures,
            "freq_bins": dict(struct_freq_bins),
            "top_10": [(s, c) for s, c in top_structures]
        },
        "quantifiers": {
            "total_quantifiers": dict(quant_counts),
            "entropy": quant_entropy,
            "transitions": dict(quant_transitions)
        },
        "reasoning_complexity": {
            "graph_depth_distribution": {
                "mean": sum(graph_depths) / len(graph_depths),
                "max": max(graph_depths),
                "min": min(graph_depths),
                "distribution": dict(Counter(graph_depths))
            },
            "branching_factor": {
                "mean": sum(graph_branching_factors) / len(graph_branching_factors),
                "max": max(graph_branching_factors),
                "min": min(graph_branching_factors)
            },
            "premise_counts_dist": dict(Counter(premise_counts)),
            "connective_complexity_dist": {
                "mean": sum(connective_complexities) / len(connective_complexities),
                "max": max(connective_complexities),
                "min": min(connective_complexities),
                "distribution": dict(Counter(connective_complexities))
            },
            "quantifier_nesting_dist": dict(Counter(quantifier_nestings))
        },
        "operators_coverage": operators_coverage,
        "similarity": {
            "nl_jaccard_gt_0.9_pairs": high_sim_pairs,
            "exact_logic_pairs": exact_logic_pairs,
            "both_duplicates_pairs": both_duplicates
        },
        "difficulty_distribution": dict(difficulty_counts)
    }

    with open('scratch/analysis_metrics.json', 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)
    print("Done! Results written to scratch/analysis_metrics.json")

if __name__ == "__main__":
    main()
