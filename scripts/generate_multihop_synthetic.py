#!/usr/bin/env python3
import json
import random
import z3
import re
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parents[1]

# Vocabulary pools for natural language generation
FANTASY_ENTITIES = [
    "Zylok", "Glipglop", "Gorgon", "Snorky", "Quibble", "Xeloda", "Pluto", 
    "Vortex", "Zorblax", "Gromble", "Wobble", "Blinky", "Sputter", "Clinker", 
    "Spike", "Nebula", "Cosmo", "Rogue", "Pixel", "Quark", "Nova", "Cipher"
]

FANTASY_CLASSES = [
    "Glipglopian", "Zorblaxian", "Gromble creature", "Nebula beast", "Vortex entity", 
    "cyber-organism", "stellar voyager", "quantum particle", "crypto-sprite", "cosmic traveler"
]

# Unary predicates vocabulary
FANTASY_PREDICATES = [
    # Verbs / properties
    {"nl_verb": "blorps", "nl_adj": "blorping", "fol": "Blorp"},
    {"nl_verb": "gleeps", "nl_adj": "gleeping", "fol": "Gleep"},
    {"nl_verb": "zazzes", "nl_adj": "zazzing", "fol": "Zazz"},
    {"nl_verb": "froozes", "nl_adj": "froozing", "fol": "Frooz"},
    {"nl_verb": "splooshes", "nl_adj": "splooshing", "fol": "Sploosh"},
    {"nl_verb": "kazams", "nl_adj": "kazaming", "fol": "Kazam"},
    {"nl_verb": "chirps", "nl_adj": "chirping", "fol": "Chirp"},
    {"nl_verb": "plonks", "nl_adj": "plonking", "fol": "Plonk"},
    {"nl_verb": "spiffs", "nl_adj": "spiffing", "fol": "Spiff"},
    {"nl_verb": "futzes", "nl_adj": "futzing", "fol": "Futz"},
    {"nl_verb": "gronks", "nl_adj": "gronking", "fol": "Gronk"},
    {"nl_verb": "snerls", "nl_adj": "snerling", "fol": "Snerl"},
    {"nl_verb": "yowls", "nl_adj": "yowling", "fol": "Yowl"},
    {"nl_verb": "zibbles", "nl_adj": "zibbling", "fol": "Zibble"},
    {"nl_verb": "squips", "nl_adj": "squipping", "fol": "Squip"},
    {"nl_verb": "wubbles", "nl_adj": "wubbling", "fol": "Wubble"}
]

def verify_with_z3(premises_fol: list[str], conclusion_fol: str, negate_conclusion: bool = True) -> tuple[str, str]:
    """
    Parses and verifies FOL entailment using Z3.
    Returns (result, error_message). result is "unsat", "sat", or "unknown".
    """
    try:
        # Simple FOL to Z3 parser for unary predicates & constants
        # Identify all predicates and constants
        preds = set()
        consts = set()
        
        all_formulas = premises_fol + [conclusion_fol]
        for f in all_formulas:
            calls = re.findall(r"\b([A-Z][A-Za-z0-9_]*)\s*\(([^()]+)\)", f)
            for p_name, arg_str in calls:
                preds.add(p_name)
                args = [a.strip() for a in arg_str.split(",")]
                for arg in args:
                    if arg not in {"x", "y", "z", "w"} and not arg.isdigit():
                        consts.add(arg)
                        
        # Define Z3 Sorts and Declares
        s = z3.Solver()
        s.set("timeout", 2000)
        
        # Object sort
        Obj = z3.DeclareSort('Object')
        
        # Declare constants
        z3_consts = {}
        for c in consts:
            z3_consts[c] = z3.Const(c, Obj)
            
        # Declare predicates as Boolean functions
        z3_preds = {}
        for p in preds:
            z3_preds[p] = z3.Function(p, Obj, z3.BoolSort())
            
        # Parse logic helper
        def to_z3_expr(formula_str, var_binding=None):
            if var_binding is None:
                var_binding = {}
                
            f_str = formula_str.strip()
            
            # Parenthesis matching helper
            def find_matching_paren(s, start_idx):
                count = 0
                for idx in range(start_idx, len(s)):
                    if s[idx] == '(':
                        count += 1
                    elif s[idx] == ')':
                        count -= 1
                        if count == 0:
                            return idx
                return -1

            # Quantifiers
            if f_str.startswith("ForAll("):
                comma_idx = f_str.find(",")
                var_name = f_str[7:comma_idx].strip()
                body_start = comma_idx + 1
                body_end = len(f_str) - 1
                body_str = f_str[body_start:body_end].strip()
                
                # Create bound variable
                z3_var = z3.Const(var_name, Obj)
                new_binding = var_binding.copy()
                new_binding[var_name] = z3_var
                
                body_expr = to_z3_expr(body_str, new_binding)
                return z3.ForAll(z3_var, body_expr)
                
            if f_str.startswith("Exists("):
                comma_idx = f_str.find(",")
                var_name = f_str[7:comma_idx].strip()
                body_start = comma_idx + 1
                body_end = len(f_str) - 1
                body_str = f_str[body_start:body_end].strip()
                
                z3_var = z3.Const(var_name, Obj)
                new_binding = var_binding.copy()
                new_binding[var_name] = z3_var
                
                body_expr = to_z3_expr(body_str, new_binding)
                return z3.Exists(z3_var, body_expr)

            # Strip outer parentheses if redundant
            if f_str.startswith("(") and f_str.endswith(")"):
                if find_matching_paren(f_str, 0) == len(f_str) - 1:
                    f_str = f_str[1:-1].strip()

            # Binary operators: <->, ->, OR, AND
            # Search from lowest precedence to highest: <->, ->, OR, AND
            for op, z3_op in [("<->", lambda a, b: a == b), ("->", z3.Implies), ("OR", z3.Or), ("AND", z3.And)]:
                # Parse considering operator precedence and parentheses
                paren_level = 0
                for idx in range(len(f_str) - len(op) + 1):
                    char = f_str[idx]
                    if char == '(':
                        paren_level += 1
                    elif char == ')':
                        paren_level -= 1
                    elif paren_level == 0:
                        if f_str[idx:idx+len(op)] == op:
                            left = to_z3_expr(f_str[:idx].strip(), var_binding)
                            right = to_z3_expr(f_str[idx+len(op):].strip(), var_binding)
                            return z3_op(left, right)
                            
            # Unary operators: NOT
            if f_str.startswith("NOT "):
                body = to_z3_expr(f_str[4:].strip(), var_binding)
                return z3.Not(body)
            if f_str.startswith("NOT("):
                body = to_z3_expr(f_str[3:].strip(), var_binding)
                return z3.Not(body)

            # Predicate call: Pred(arg)
            match = re.match(r"^([A-Z][A-Za-z0-9_]*)\s*\(([^()]+)\)$", f_str)
            if match:
                p_name = match.group(1)
                arg_name = match.group(2).strip()
                z3_p = z3_preds[p_name]
                if arg_name in var_binding:
                    z3_arg = var_binding[arg_name]
                else:
                    z3_arg = z3_consts[arg_name]
                return z3_p(z3_arg)
                
            raise ValueError(f"Failed to parse formula: {formula_str}")

        # Add premises
        for p_str in premises_fol:
            expr = to_z3_expr(p_str)
            s.add(expr)
            
        # Add conclusion
        conclusion_expr = to_z3_expr(conclusion_fol)
        if negate_conclusion:
            s.add(z3.Not(conclusion_expr))
        else:
            s.add(conclusion_expr)
            
        chk = s.check()
        return str(chk), ""
    except Exception as e:
        return "error", str(e)


def generate_chain_story(story_id: int, depth: int, local_rng: random.Random) -> list[dict]:
    """
    Generates a synthetic logical story with depth `depth`.
    Returns a list of questions (True, False, or Unknown) for this story.
    """
    # Select predicates and entities for this story
    preds = local_rng.sample(FANTASY_PREDICATES, depth + 1)
    entity = local_rng.choice(FANTASY_ENTITIES)
    creature_class = local_rng.choice(FANTASY_CLASSES)
    
    premises_nl = []
    premises_fol = []
    reasoning_steps = []
    
    # We construct implication rules along the chain: P0 -> P1 -> P2 -> ... -> P_depth
    # We will randomly introduce some variations:
    # - Biconditional (iff <->): e.g. P_i <-> P_i+1 (with probability 0.20)
    # - Negative implications (NOT): e.g. P_i -> NOT P_i+1
    # - Disjunction (OR): e.g. P_i -> (P_i+1 OR Temp)
    # - Existential (Exists): e.g. Exists(x, P_0(x) AND P_1(x))
    
    # State tracking of negation signs along the path
    # sign[i] = True if predicate P_i is positive, False if negated in the chain
    signs = [True] * (depth + 1)
    
    for i in range(depth):
        p_curr = preds[i]
        p_next = preds[i+1]
        
        # Decide connective variation
        roll = local_rng.random()
        
        curr_sign = signs[i]
        next_sign = local_rng.choice([True, False]) if roll > 0.3 else curr_sign # 30% chance to flip polarity
        signs[i+1] = next_sign
        
        fol_curr = f"{p_curr['fol']}(x)" if curr_sign else f"NOT {p_curr['fol']}(x)"
        fol_next = f"{p_next['fol']}(x)" if next_sign else f"NOT {p_next['fol']}(x)"
        
        nl_curr_active = p_curr['nl_verb'] if curr_sign else f"does not {p_curr['nl_verb'][:-1]}"
        nl_next_active = p_next['nl_verb'] if next_sign else f"does not {p_next['nl_verb'][:-1]}"
        
        if roll < 0.20 and i < depth - 1:
            # 1. Biconditional (<->)
            # FOL: ForAll(x, (A(x) <-> B(x)))
            # NL: A creature is A if and only if it B.
            fol_rule = f"ForAll(x, ({fol_curr} <-> {fol_next}))"
            nl_rule = f"A {creature_class} {nl_curr_active} if and only if it {nl_next_active}."
            reasoning_step = f"From Premise: '{p_curr['fol']}(x) <-> {p_next['fol']}(x)'"
        elif roll < 0.40 and i < depth - 1:
            # 2. Disjunction (OR)
            # We can state: A(x) -> (B(x) OR Extra(x)), but to make it deterministic we can state:
            # NOT B(x) -> NOT A(x) etc.
            # Let's do simple implication but verbalized with "either or" if negated:
            # FOL: ForAll(x, (A(x) -> B(x)))
            fol_rule = f"ForAll(x, ({fol_curr} -> {fol_next}))"
            nl_rule = f"If a {creature_class} {nl_curr_active}, then it {nl_next_active}."
            reasoning_step = f"From Premise: '{p_curr['fol']}(x) -> {p_next['fol']}(x)'"
        else:
            # 3. Standard Implication (->)
            fol_rule = f"ForAll(x, ({fol_curr} -> {fol_next}))"
            nl_rule = f"If a {creature_class} {nl_curr_active}, then it {nl_next_active}."
            reasoning_step = f"From Premise: '{p_curr['fol']}(x) -> {p_next['fol']}(x)'"
            
        premises_nl.append(nl_rule)
        premises_fol.append(fol_rule)
        
    # Add base fact: P_0(entity) is True or False or Existential
    base_roll = local_rng.random()
    if base_roll < 0.25:
        # Existential base: Exists(x, P_0(x) AND Creature(x))
        # NL: There is a creature that blorps.
        fol_fact = f"Exists(x, ({preds[0]['fol']}(x)))"
        nl_fact = f"There exists a {creature_class} that {preds[0]['nl_verb']}."
        premises_nl.append(nl_fact)
        premises_fol.append(fol_fact)
        reasoning_steps.append(f"Base Existential Fact: Exists(x, {preds[0]['fol']}(x)) exists.")
        target_entity = "some creature"
        is_existential = True
    else:
        # Constant base: P_0(entity)
        # NL: Zylok blorps.
        fol_fact = f"{preds[0]['fol']}({entity.lower()})"
        nl_fact = f"{entity} is a {creature_class} that {preds[0]['nl_verb']}."
        premises_nl.append(nl_fact)
        premises_fol.append(fol_fact)
        reasoning_steps.append(f"Base Fact: {preds[0]['fol']}({entity.lower()}) is True.")
        target_entity = entity
        is_existential = False

    # Generate CoT deduction steps
    curr_state = f"{preds[0]['fol']}" if not is_existential else f"Exists(x, {preds[0]['fol']}(x))"
    curr_subject = entity.lower() if not is_existential else "x"
    
    cot_steps = [
        f"Step 1: Identify premises. We have a logic chain of implications and a base fact."
    ]
    if is_existential:
        cot_steps.append(f"Step 2: Base fact tells us there exists some object x such that {preds[0]['fol']}(x) is True.")
    else:
        cot_steps.append(f"Step 2: Base fact tells us {entity} ({entity.lower()}) satisfies {preds[0]['fol']}({entity.lower()}).")
        
    for i in range(depth):
        p_curr = preds[i]
        p_next = preds[i+1]
        curr_sign = signs[i]
        next_sign = signs[i+1]
        
        fol_curr_item = f"{p_curr['fol']}({curr_subject})" if curr_sign else f"NOT {p_curr['fol']}({curr_subject})"
        fol_next_item = f"{p_next['fol']}({curr_subject})" if next_sign else f"NOT {p_next['fol']}({curr_subject})"
        
        nl_curr_desc = f"{p_curr['nl_verb']}" if curr_sign else f"does not {p_curr['nl_verb'][:-1]}"
        nl_next_desc = f"{p_next['nl_verb']}" if next_sign else f"does not {p_next['nl_verb'][:-1]}"
        
        step_num = i + 3
        if is_existential:
            cot_steps.append(
                f"Step {step_num}: Applying rule '{p_curr['fol']}(x) -> {p_next['fol']}(x)' to the existential variable x, "
                f"since we know {fol_curr_item}, we deduce {fol_next_item} by Modus Ponens."
            )
        else:
            cot_steps.append(
                f"Step {step_num}: Applying rule '{p_curr['fol']}(x) -> {p_next['fol']}(x)' to {entity}, "
                f"since we know {fol_curr_item}, we deduce {fol_next_item} by Modus Ponens."
            )

    # Let's verify and construct questions
    # Question 1: Entailed conclusion (True)
    # Question 2: Contradicted conclusion (False)
    # Question 3: Unrelated conclusion (Unknown)
    
    questions = []
    
    # Q1: Entailed (True)
    last_sign = signs[-1]
    last_pred = preds[-1]
    
    if is_existential:
        fol_q1 = f"Exists(x, ({last_pred['fol']}(x)))" if last_sign else f"Exists(x, (NOT {last_pred['fol']}(x)))"
        nl_q1 = f"Does there exist a {creature_class} that {last_pred['nl_verb']}?" if last_sign else f"Does there exist a {creature_class} that does not {last_pred['nl_verb'][:-1]}?"
    else:
        fol_q1 = f"{last_pred['fol']}({entity.lower()})" if last_sign else f"NOT {last_pred['fol']}({entity.lower()})"
        nl_q1 = f"Does {entity} {last_pred['nl_verb']}?" if last_sign else f"Does {entity} not {last_pred['nl_verb'][:-1]}?"
        
    res_q1, err1 = verify_with_z3(premises_fol, fol_q1, negate_conclusion=True)
    
    if res_q1 == "unsat":  # Premises AND NOT Q1 is unsat -> Q1 is entailed (True)
        q1_cot = list(cot_steps)
        final_step = len(q1_cot) + 1
        if is_existential:
            q1_cot.append(f"Step {final_step}: We have deduced that there exists some creature x satisfying the final condition. Therefore, the answer is Yes (True).")
        else:
            q1_cot.append(f"Step {final_step}: We have deduced that {entity} satisfies the final predicate. Therefore, the answer is Yes (True).")
            
        questions.append({
            "premises-NL": premises_nl,
            "premises-FOL": premises_fol,
            "question": nl_q1,
            "answer": "True",
            "cot": q1_cot,
            "explanation": f"Based on the base fact and the transitive implication chain of depth {depth}, we can step-by-step deduce that {nl_q1.replace('Does ', '').replace('?', '')} is correct.",
            "dataset_source": "synthetic_multihop_true",
            "example_id": f"synthetic_mh_{story_id}_q1",
            "split": "train"
        })
        
    # Q2: Contradicted (False)
    # Negate the correct answer to make it false
    if is_existential:
        fol_q2 = f"Exists(x, (NOT {last_pred['fol']}(x)))" if last_sign else f"Exists(x, ({last_pred['fol']}(x)))"
        nl_q2 = f"Does there exist a {creature_class} that does not {last_pred['nl_verb'][:-1]}?" if last_sign else f"Does there exist a {creature_class} that {last_pred['nl_verb']}?"
    else:
        fol_q2 = f"NOT {last_pred['fol']}({entity.lower()})" if last_sign else f"{last_pred['fol']}({entity.lower()})"
        nl_q2 = f"Does {entity} not {last_pred['nl_verb'][:-1]}?" if last_sign else f"Does {entity} {last_pred['nl_verb']}?"
        
    res_q2, err2 = verify_with_z3(premises_fol, fol_q2, negate_conclusion=False) # Check if Q2 is inconsistent
    if res_q2 == "unsat": # Premises AND Q2 is unsat -> Q2 is impossible (False)
        q2_cot = list(cot_steps)
        final_step = len(q2_cot) + 1
        q2_cot.append(f"Step {final_step}: The derived logical consequence directly contradicts the question. Therefore, the answer is No (False).")
        
        questions.append({
            "premises-NL": premises_nl,
            "premises-FOL": premises_fol,
            "question": nl_q2,
            "answer": "False",
            "cot": q2_cot,
            "explanation": f"The chain of logic establishes that the opposite of this question must hold. Thus, the statement is false.",
            "dataset_source": "synthetic_multihop_false",
            "example_id": f"synthetic_mh_{story_id}_q2",
            "split": "train"
        })

    # Q3: Unknown (Uncertain)
    # We ask about an unrelated predicate that is not in the chain
    all_pred_names = {p['fol'] for p in preds}
    unrelated_pred = None
    for p in FANTASY_PREDICATES:
        if p['fol'] not in all_pred_names:
            unrelated_pred = p
            break
            
    if unrelated_pred:
        if is_existential:
            fol_q3 = f"Exists(x, ({unrelated_pred['fol']}(x)))"
            nl_q3 = f"Does there exist a {creature_class} that {unrelated_pred['nl_verb']}?"
        else:
            fol_q3 = f"{unrelated_pred['fol']}({entity.lower()})"
            nl_q3 = f"Does {entity} {unrelated_pred['nl_verb']}?"
            
        res_q3_t, _ = verify_with_z3(premises_fol, fol_q3, negate_conclusion=True)
        res_q3_f, _ = verify_with_z3(premises_fol, fol_q3, negate_conclusion=False)
        
        if res_q3_t != "unsat" and res_q3_f != "unsat":
            # Neither entailed nor contradicted -> Unknown
            q3_cot = [
                f"Step 1: Identify the premises.",
                f"Step 2: Examine the question regarding the property '{unrelated_pred['fol']}'.",
                f"Step 3: Scan the premises for any occurrences of '{unrelated_pred['fol']}'. There are no rules or facts containing it.",
                f"Step 4: Since the predicate is entirely unconstrained by the premises, we cannot determine its truth value. Therefore, the answer is Uncertain (Unknown)."
            ]
            questions.append({
                "premises-NL": premises_nl,
                "premises-FOL": premises_fol,
                "question": nl_q3,
                "answer": "Unknown",
                "cot": q3_cot,
                "explanation": f"The premises do not mention the property of {unrelated_pred['nl_adj']} at all, making it logically independent and uncertain.",
                "dataset_source": "synthetic_multihop_unknown",
                "example_id": f"synthetic_mh_{story_id}_q3",
                "split": "train"
            })
            
    return questions

def main():
    print("=" * 80)
    print("GENERATING SYNTHETIC MULTI-HOP LOGIC STORIES...")
    print("=" * 80)
    
    # Seed local random for reproducibility
    local_rng = random.Random(2026)
    
    synthetic_samples = []
    
    # Generate 150 stories with varying depths (4 to 7 steps)
    story_id = 0
    for depth in [4, 5, 6, 7]:
        # Number of stories per depth level
        num_stories = 40 if depth < 6 else 35
        print(f"Generating {num_stories} stories of depth {depth}...")
        for _ in range(num_stories):
            qs = generate_chain_story(story_id, depth, local_rng)
            synthetic_samples.extend(qs)
            story_id += 1
            
    # Save output
    output_path = root_dir / "data" / "processed" / "logic_synthetic_multihop.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(synthetic_samples, f, indent=2, ensure_ascii=False)
        
    print("-" * 80)
    print(f"Generated {len(synthetic_samples)} synthetic multi-hop question samples.")
    print(f"Saved to: {output_path}")
    print("=" * 80)

if __name__ == "__main__":
    main()
