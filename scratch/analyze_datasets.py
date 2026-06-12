import os
import json
import numpy as np
from transformers import AutoTokenizer

# Paths
MODEL_ID = "d:/mduy/source/repos/EXACT/model_cache"
PHYSICS_PATH = "d:/mduy/source/repos/EXACT/data/processed/physics_distillation.json"
ROUTER_PATH = "d:/mduy/source/repos/EXACT/data/processed/router_dataset.json"

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

</OPERATING_CONSTRAINTS>""".strip()

router_system_prompt = """# Role
You are an expert Physics and Mathematical Reasoner acting as a strict Semantic Classification Router. Your sole task is to analyze problems and map them to their exact domains and operational states based on the rules below, without solving the problem itself.

# Router Configuration

## Domain Options
Physics domains:
- electrostatic_force
- electrostatic_field
- ac_impedance
- resonance
- frequency_scaling
- electromagnetism
- oscillation_energy
- circuit_power
- capacitance_and_energy
- experimental_physics

Reasoning domains:
- spatial_vector_geometry
- qualitative_reasoning
- symbolic_derivation
- proportional_scaling
- error_analysis

## Domain Selection Rules

### spatial_vector_geometry
MANDATORY when: The problem text introduces spatial positioning, coordinate paths, or multi-point labels (such as points A, B, and C) that dictate relative distances or non-collinear structures. 
CRITICAL: If a core physics domain applies to a system with multiple non-co-located spatial coordinates, you must output this domain alongside the physics domain. Do not omit it.
- IMPLICATION: Directs the downstream logic to parse spatial and matrix vectors.

### experimental_physics
Use when: Experimental measurements, trial data sets, absolute or relative uncertainties, instrument tolerances, or duplicate measurement values.

### capacitance_and_energy
Use when: Parallel-plate configurations, dielectric replacement/materials, electrostatic potential energy storage. Look for variables normalized strictly to base Coulombs (e.g., 'e-6 C', 'e-7 C'), base Farads (e.g., 'e-5 F', 'F'), or area/separations scaled to meters or square meters (e.g., 'm', 'm^2').

### error_analysis
Use when: Random error, percentage relative error, standard deviation, range-based uncertainty, or error propagation.

### proportional_scaling
Use when: The problem relies on qualitative ratio behaviors, relative trends, or fractional multiplier adjustments (e.g., "if the resistance doubles", "halves", or "is cut in a 1:3 ratio") without presenting absolute initial values.
- IMPLICATION: Directs downstream logic to evaluate mathematical behavior scaling trends instead of raw value evaluations.

### electrostatic_force
Use when: Coulomb interactions, electric force, attractive/repulsive forces, or point charge mechanics.

### electrostatic_field
Use when: Electric field intensity (E), flux lines, field distribution, or co-located vertex field calculations.

### ac_impedance
Use when: RLC alternating current series circuits, phasor geometry, component voltages, or phase angle calculations. Look for variables normalized to base Ohm units ('ohm') and alternating current frequencies normalized strictly to Hertz ('Hz').

### resonance
Use when: Reactance cancellations (XL == XC), maximum AC current states, zero phase angles, or resonant frequency calculations.

### frequency_scaling
Use when: System frequency shifts, omega transformations, or non-linear adjustments to reactance. Look for multiple sequential frequencies scaled strictly to base Hertz ('Hz').

### electromagnetism
Use when: Magnetic flux, flux linkage, inductive EMF, self-inductance (L), solenoids, or magnetic energy density.

### oscillation_energy
Use when: LC circuit energy conservation, continuous exchange between electric and magnetic energies, or fraction of maximum energy states.

### circuit_power
Use when: DC power, AC average power, power factors, Joule heating, or parallel multi-branch entity calculations.

### qualitative_reasoning
Use when: The question is entirely conceptual, descriptive, or requires a binary confirmation, but completely lacks mathematical metrics, percentages, multipliers, or numerical scale factors.
- IMPLICATION: Directs downstream logic to output a raw text description list or a strict "Yes"/"No" string response.

## Additional Field
### multi_state
Set true when problem contains: before/after states, transformed systems, frequency changes, or state transitions. Otherwise set false.

## OUTPUT FORMAT
{
  "domains": ["domain1", "domain2"],
  "multi_state": true
}

## Strict Operational Directives:
- You must output EXACTLY one valid JSON object.
- Absolutely NO markdown wrapping (do not use ```json or ```).
- Absolutely NO explanations, introductory text, or closing text.
- Do not include chain-of-thought processing or reasoning text in the output.
  
## Structural Pairing Rules
- For any problem describing explicit coordinates... the "domains" array 
  MUST contain the primary physics domain and "spatial_vector_geometry". 
  A third domain may be added when applicable (e.g., "symbolic_derivation").
- CONCEPTUAL PAIRING GUARD: If a problem completely lacks relative physical distances, layout structures, or spatial coordinates (e.g., purely descriptive circuit loops or trend predictions), you are strictly BANNED from outputting "spatial_vector_geometry". Instead, you must pair the physics domain with its corresponding conceptual reasoning framework:
  - If it features text trend movements or binary attributes: ["physics_domain", "qualitative_reasoning"]
  - If it features multiplier/fractional factors ("doubles", "halves"): ["physics_domain", "proportional_scaling"]
- BANNED: Never drop a required reasoning domain for multi-variable or structural configurations. Never output a single-element array for spatial layout problems. Never output more than three domain elements under any circumstances.
- BANNED: Do not use the instruction "Prefer specific domains over broad ones."
"""

def analyze_dataset(name, path, system_prompt, is_router=False):
    print(f"--- Analyzing {name} dataset: {path} ---")
    if not os.path.exists(path):
        print(f"Error: {path} does not exist!")
        return None
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Total samples: {len(data)}")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    total_tokens = []
    prompt_tokens = []
    response_tokens = []
    
    for item in data:
        inp = item.get("input", "")
        out = item.get("output", "")
        
        if is_router:
            user_content = f"<QUESTION>\n{inp.strip()}\n</QUESTION>"
        else:
            user_content = inp.strip()
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": out.strip()}
        ]
        
        # Format using chat template
        full_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        prompt_messages = messages[:-1]
        prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        
        # Tokenize
        full_tokens = tokenizer(full_text)["input_ids"]
        p_tokens = tokenizer(prompt_text)["input_ids"]
        r_tokens = full_tokens[len(p_tokens):] # Approximate target response tokens (since tokenizer is causal, they align well)
        
        total_tokens.append(len(full_tokens))
        prompt_tokens.append(len(p_tokens))
        response_tokens.append(len(r_tokens))
        
    stats = {
        "total": {
            "mean": np.mean(total_tokens),
            "median": np.median(total_tokens),
            "min": np.min(total_tokens),
            "max": np.max(total_tokens),
            "p90": np.percentile(total_tokens, 90),
            "p95": np.percentile(total_tokens, 95),
            "p99": np.percentile(total_tokens, 99)
        },
        "prompt": {
            "mean": np.mean(prompt_tokens),
            "median": np.median(prompt_tokens),
            "min": np.min(prompt_tokens),
            "max": np.max(prompt_tokens),
            "p90": np.percentile(prompt_tokens, 90),
            "p95": np.percentile(prompt_tokens, 95),
            "p99": np.percentile(prompt_tokens, 99)
        },
        "response": {
            "mean": np.mean(response_tokens),
            "median": np.median(response_tokens),
            "min": np.min(response_tokens),
            "max": np.max(response_tokens),
            "p90": np.percentile(response_tokens, 90),
            "p95": np.percentile(response_tokens, 95),
            "p99": np.percentile(response_tokens, 99)
        }
    }
    
    print("\nToken Statistics:")
    for key, values in stats.items():
        print(f"  {key.capitalize()} tokens:")
        print(f"    Min: {values['min']}")
        print(f"    Max: {values['max']}")
        print(f"    Mean: {values['mean']:.2f}")
        print(f"    Median: {values['median']}")
        print(f"    P90: {values['p90']:.2f}")
        print(f"    P95: {values['p95']:.2f}")
        print(f"    P99: {values['p99']:.2f}")
        
    if is_router:
        # Analyze router domains
        domain_counts = {}
        multi_state_count = 0
        for item in data:
            try:
                out_json = json.loads(item.get("output", "{}"))
                domains = out_json.get("domains", [])
                for d in domains:
                    domain_counts[d] = domain_counts.get(d, 0) + 1
                if out_json.get("multi_state", False):
                    multi_state_count += 1
            except Exception:
                pass
        print("\nRouter Domain Counts:")
        for d, c in sorted(domain_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {d}: {c} ({c/len(data)*100:.2f}%)")
        print(f"  Multi-state count: {multi_state_count} ({multi_state_count/len(data)*100:.2f}%)")
        
    return stats

if __name__ == "__main__":
    phys_stats = analyze_dataset("Physics", PHYSICS_PATH, physics_system_prompt, is_router=False)
    print("\n" + "="*50 + "\n")
    router_stats = analyze_dataset("Router", ROUTER_PATH, router_system_prompt, is_router=True)
