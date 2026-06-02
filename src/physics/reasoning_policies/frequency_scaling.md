# frequency_scaling.md

## 1. RELATIONSHIPS
- XL = omega * L
- XC = 1 / (omega * C)
- R_new = R_0

## 2. STATE TRANSFORMATION
- If omega_new = k * omega_0:
  - XL_new = k * XL_0
  - XC_new = XC_0 / sp.Float(k)
- BANNED: Floating-point division on k in raw Python. Use SymPy fractions.

## 3. QUALITATIVE TREND ROUTING
- If the question asks for a qualitative behavioral change, ans must hold a lowercase text string primitive list, not a float value.
- Evaluate Ratio = State_new / State_0 and map via conditional loops.
- Code Template: `ratio = I_new / I_0; ans = ['decreases by half'] if ratio == sp.Float('0.5') else ['changed']; unit = ['-']`
- BANNED: round(), trailing semicolons.