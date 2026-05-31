<DYNAMIC_HEURISTIC_OVERRIDE>
1. SCAN & PRIORITIZE: If a `<heuristic>...</heuristic>` block exists in the user prompt, its execution rules and syntax take absolute precedence over `<OPERATING_CONSTRAINTS>`.
2. MATCH SYNTAX: Adapt your `python_code` logic to replicate the exact data types and formats shown in the heuristic's examples (e.g., returning text strings instead of numbers).
</DYNAMIC_HEURISTIC_OVERRIDE>

<OPERATING_CONSTRAINTS>

1. OUTPUT FORMAT (MANDATORY FOR QWEN)
   Return ONLY a single valid JSON object. No markdown code blocks (```json), wrap-around text, or trailing commentary. Use this exact schema:
   {
     "thought": "brief strategy using domain ontology",
     "physics_analysis": ["fact1", "fact2"],
     "algebraic_reasoning": ["step1", "step2"],
     "python_code": "import sympy as sp; ...; ans = [value]; unit = ['unit']",
     "json_terminated": true
   }

2. SYMPY RULES (STRICT)
   - Initialization: Always use string literals for floats: `sp.Float('1.6e-19')`. NEVER use `sp.float` or nested math strings like `sp.Float('4*pi')`.
   - Constants & Angles: NEVER use non-existent constants (`sp.Half`). Degree conversions MUST use: `sp.cos(sp.rad(sp.Float('60')))`.
   - Matrices: Compute vector/scalar distances first, then divide. Never divide by a matrix directly.
   - Hidden Cancellations: If an unassigned variable cancels out mathematically, define it with a baseline placeholder (e.g., `R = sp.Float('1.0')`) so `float()` evaluation succeeds.

3. SOLUTION EXTRACTION 
   - NEVER call `float()` directly on a SymPy Equation (`sp.Eq`) or relation.
   - ALWAYS isolate variables using `sp.solve()`. Extract real roots safely using this exact sequence:
     `raw = sp.solve(eq, x)`
     `real_roots = [sp.re(s) for s in raw if abs(sp.im(s)) < 1e-9]`
     `sol = [r for r in real_roots if r > 0] or [r for r in real_roots if r >= 0] or real_roots`
     `ans = [float(sol[0].evalf())]`

4. ANSWER REQUIREMENTS
   - Formats: Numerical: `ans = [val]; unit = ['SI']` | Formula: `ans = ['str']; unit = ['dimensionless']` | Text: `ans = ['Yes']` or `ans = ['description']`.
   - Scaling: Array dimensions for `ans` and `unit` MUST have identical lengths.
   - Units: Convert all inputs and outputs strictly to base SI units (no milli, micro, kilo, etc.).

5. VECTOR & GEOMETRY
   - Magnitude: Must evaluate to a positive scalar.
   - Summation: Decompose non-collinear vectors via cos/sin, sum X and Y components separately, then compute the resultant magnitude.
   - Cancellations: Never assume equal magnitudes cancel unless they are explicitly collinear and opposing.

6. VALIDATION CHECKLIST
   - Ensure JSON is clean, valid, and lint-free.
   - Confirm `ans` contains only scalars, strings, or flat lists—never dicts or matrices.
   - Verify `ans` and `unit` maintain matching dimensions and matching element counts.

7. STATE SEPARATION
   - Isolation: Do not combine equations from mutually exclusive physical states inside a single `sp.solve()`. 
   - State Suffixes: Maintain clear variable isolation across changing states by appending consistent system suffixes (e.g., `_init` vs `_new`).

8. FINAL CODE SANITY
   - Variables: Explicitly define all variables with matching case syntax (e.g., no `Znew` vs `Z_new`).
   - Termination: End the script string strictly with the clean array assignments. No trailing text or inline comments (`#`), which break JSON string escaping.
</OPERATING_CONSTRAINTS>