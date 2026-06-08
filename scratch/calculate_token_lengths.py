import os
import json
import sys
from transformers import AutoTokenizer

def count_tokens():
    model_id = r"d:\mduy\source\repos\EXACT\model_cache"
    merged_path = r"d:\mduy\source\repos\EXACT\data\processed\logic_merged_valid_augmented.json"
    physics_path = r"d:\mduy\source\repos\EXACT\data\processed\physics_distillation.json"

    print("Loading tokenizer from cache...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True, local_files_only=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Loading datasets...")
    with open(merged_path, "r", encoding="utf-8") as f:
        fol_data = json.load(f)
    with open(physics_path, "r", encoding="utf-8") as f:
        physics_data = json.load(f)

    print(f"Loaded {len(fol_data)} raw FOL samples.")
    print(f"Loaded {len(physics_data)} raw Physics samples.")

    system_prompt_template = (
        "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
        "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n"
        "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\n\n"
        "ALLOWED OPERATORS:\n"
        "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
        "QUANTIFIER RULES:\n"
        "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
        "Return JSON only."
    )

    user_prompt_template = (
        "Convert the following {num_premises} premises into canonical first-order logic.\n\n"
        "Premises:\n"
        "{premises}\n\n"
        "Return a JSON list of exactly {num_premises} strings containing the formulas, in the exact same order."
    )

    physics_system_prompt = """You are a precise physics reasoning agent.

TASK:
Convert a physics problem and any provided reasoning policies into executable SymPy code and a valid JSON response.

<REASONING_POLICY_OVERRIDE>

A <reasoning_policies> block may be provided.

If present:

1. Treat it as the primary reasoning guidance.

2. Follow its definitions, representations, topology rules,
   coordinate conventions, state models, and solution procedures.

3. Apply the underlying reasoning pattern rather than copying
   example expressions verbatim.

4. Override a policy only when required for:
   - physical validity
   - mathematical validity
   - SymPy executability

</REASONING_POLICY_OVERRIDE>

<OPERATING_CONSTRAINTS>

Return ONLY:

{
  "thought": "...",
  "physics_analysis": [...],
  "algebraic_reasoning": [...],
  "python_code": "...",
  "json_terminated": true
}

thought format:

<detected structure>. <activated reasoning pattern>. <solution strategy>.

thought:
- concise
- high-level
- no calculations
- no intermediate values
- no final values

physics_analysis:
- concise policy-grounded physical interpretation
- record relevant physical facts, assumptions, states, or constraints
- no calculations
- no final values

algebraic_reasoning:
- concise policy-grounded symbolic procedure
- describe the intended solve workflow
- no calculations
- no final values

python_code:
- begin with "import sympy as sp"
- use sp.Float(...) for numerical constants
- define variables before use
- solve symbolically before numeric evaluation
- evaluate norms, distances, and square roots using float(...) or .evalf()
- single-line string only
- separate statements using "; "
- no loops
- no functions
- no conditional branches
- no newline characters

Final code statements must define:

ans = [...]
unit = [...]

Requirements:
- ans must be a list
- unit must be a list
- len(ans) == len(unit)
- use raw SymPy-computed values
- do not manually round or format values
- no trailing semicolon after the final statement

Use SI base or SI derived units only.
Do not use engineering-prefix units.

Return the JSON object only.

</OPERATING_CONSTRAINTS>"""

    # Format unique FOL samples
    seen_premises = set()
    fol_formatted = []
    for item in fol_data:
        nl_list = item.get("premises-NL", [])
        fol_list = item.get("premises-FOL", [])
        if not nl_list or not fol_list or len(nl_list) != len(fol_list):
            continue
        nl_serialized = "\n".join(nl_list)
        if nl_serialized in seen_premises:
            continue
        seen_premises.add(nl_serialized)

        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\n"
        user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
        assistant_response = json.dumps(fol_list, indent=2)

        messages = [
            {"role": "system", "content": system_prompt_template},
            {"role": "user", "content": user_prompt.strip()},
            {"role": "assistant", "content": assistant_response.strip()}
        ]
        fol_formatted.append(messages)

    # Format Physics samples
    phys_formatted = []
    for item in physics_data:
        inp = item.get("input", "")
        out = item.get("output", "")
        if inp and out:
            messages = [
                {"role": "system", "content": physics_system_prompt},
                {"role": "user", "content": inp.strip()},
                {"role": "assistant", "content": out.strip()}
            ]
            phys_formatted.append(messages)

    print(f"Unique FOL samples for training: {len(fol_formatted)}")
    print(f"Physics samples for training: {len(phys_formatted)}")

    # Count tokens
    print("\nCounting tokens for FOL...")
    fol_tokens = []
    for idx, msg in enumerate(fol_formatted):
        text = tokenizer.apply_chat_template(msg, tokenize=False, add_generation_prompt=False)
        toks = tokenizer.encode(text)
        fol_tokens.append(len(toks))
        if idx % 1000 == 0 and idx > 0:
            print(f"Processed {idx} samples...")

    print("Counting tokens for Physics...")
    phys_tokens = []
    for idx, msg in enumerate(phys_formatted):
        text = tokenizer.apply_chat_template(msg, tokenize=False, add_generation_prompt=False)
        toks = tokenizer.encode(text)
        phys_tokens.append(len(toks))
        if idx % 1000 == 0 and idx > 0:
            print(f"Processed {idx} samples...")

    print("\n=== FOL token statistics ===")
    print(f"Total tokens: {sum(fol_tokens)}")
    print(f"Mean tokens per sample: {sum(fol_tokens)/len(fol_tokens):.2f}")
    print(f"Max tokens per sample: {max(fol_tokens)}")

    print("\n=== Physics token statistics ===")
    print(f"Total tokens: {sum(phys_tokens)}")
    print(f"Mean tokens per sample: {sum(phys_tokens)/len(phys_tokens):.2f}")
    print(f"Max tokens per sample: {max(phys_tokens)}")

if __name__ == "__main__":
    count_tokens()
