import os
from transformers import AutoTokenizer

MODEL_DIR = r"d:\mduy\source\repos\EXACT\model_cache"

print("Loading tokenizer from:", MODEL_DIR)
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, trust_remote_code=True, local_files_only=True)

system_prompt_template_fol = (
    "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n"
    "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\n\n"
    "ALLOWED OPERATORS:\n"
    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
    "QUANTIFIER RULES:\n"
    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
    "Return JSON only."
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

fol_msg = [
    {"role": "system", "content": system_prompt_template_fol},
    {"role": "user", "content": "test user prompt"}
]
fol_text = tokenizer.apply_chat_template(fol_msg, tokenize=False, add_generation_prompt=True)
fol_tokens = tokenizer.encode(fol_text)

phys_msg = [
    {"role": "system", "content": physics_system_prompt},
    {"role": "user", "content": "test user prompt"}
]
phys_text = tokenizer.apply_chat_template(phys_msg, tokenize=False, add_generation_prompt=True)
phys_tokens = tokenizer.encode(phys_text)

print("\nFOL Prompt prefix tokens (first 25):")
print(fol_tokens[:25])
print([tokenizer.decode([t]) for t in fol_tokens[:25]])

print("\nPhysics Prompt prefix tokens (first 25):")
print(phys_tokens[:25])
print([tokenizer.decode([t]) for t in phys_tokens[:25]])
