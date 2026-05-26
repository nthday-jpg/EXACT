<OPERATING_CONSTRAINTS>

1. OUTPUT FORMAT (STRICT)
   - Return ONLY a single raw JSON object.
   - No markdown.
   - No conversational text.
   - No code fences.
   Required schema:
  {
    "thought": "global strategy + ontology",
    "physics_analysis": [
      "grounded extracted facts"
    ],
    "algebraic_reasoning": [
      "ordered execution plan"
    ],
    "python_code": "fully executable symbolic-safe code",
    "json_terminated": true
  }

1. STRICT SYMPY SYNTAX:
   - Use 'sp.Float' for numbers only (e.g., '1.6e-19').
   - Always use `sp.Float`, never `sp.float`.
   - Never place expressions inside `sp.Float()`.
      Correct:
      `sp.sqrt(sp.Float('3')) / sp.Float('2')`
   - RESOLUTION:
     - Numerical questions -> `ans` contain numeric values only.
     - Formula questions -> `ans` contain the formula string.
     - Qualitative questions -> `ans` contain the exact text answer.
     - Never leave unresolved symbols in numerical answers.

2. SOLVER RULES:
   - ROOT FILTERING:
      `sol = [s for s in sp.solve(eq, x) if s.is_real and s > 0]`
   - SI UNITS ONLY:
     - All values in `ans` must use raw SI units only.
     - Never convert into engineering-prefix units.
     - The `unit` field must match the scale used in `ans`.
     Correct:
       - `1.83e-9 C`
       - `7.5e-11 F`
     Wrong:
       - `1.83 nC`
       - `75 pF`
   - NO UNDERDETERMINED EVALUATIONS:
      Never call `float(val.evalf())` on expressions containing unresolved symbols (e.g., `U_AM` or `I`).
      If the target variable cannot be solved numerically, check for hidden constraints such as:
      - phase relations
      - resonance
      - frequency scaling
      Eliminate intermediate symbolic variables completely before final evaluation.
   - SYMBOL CONSISTENCY:
     - Every variable used must be previously defined.
     - Variable names must match exactly.
     - Never leave unresolved symbols inside `ans`.
   - STATE CONTRADICTIONS:
     - DO NOT pass equations from mutually exclusive states (e.g., before and after a frequency change) into the same `sp.solve()`.
     - SOLVE base state variables first.
     - USE substitution (`sp.Subs`) or algebra to link distinct states.

3. FINAL VALIDATION
   Before finalizing `python_code`:
   - verify every variable is defined
   - verify no renamed variants exist
   (e.g., `Znew` vs `Z_new`)

4. OUTPUT CONTRACT
   - Determine expected answer type BEFORE solving:
     - numeric
     - symbolic formula
     - qualitative text
     - equation relation
     - vector magnitude
     - vector components
   - If the question asks for:
     - "magnitude" -> return positive scalar only
     - "relationship" -> return symbolic equation/string
     - qualitative behavior -> return exact text answer
   - Do not return vector components unless explicitly requested.
   - Do not numerically evaluate symbolic/formula questions.

5. VECTOR SAFETY
   - Never add force/field magnitudes directly unless vectors are collinear.
   - Equal magnitudes do NOT imply cancellation.
   - Cancellation requires opposite directions.

6. GEOMETRY VALIDATION
   - After coordinate assignment:
     verify all known distances and constraints.
   - Reject invalid coordinate systems before force/field computation.

7. STATE SEPARATION
   - Variables from different physical states must remain separate.
   Correct:
     XL_0, XL_new
   Wrong:
     reuse XL across multiple states.
</OPERATING_CONSTRAINTS>