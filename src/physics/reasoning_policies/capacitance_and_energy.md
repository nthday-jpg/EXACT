# capacitance_and_energy.md

## 1. EQUATIONS
- C = eps0 * S / d
- U = Q**2 / (sp.Float('2') * C)
- U = sp.Float('0.5') * C * V**2
- eps0 = sp.Float('8.854187817e-12')

## 2. RATIO RULES
- If inputs lack numerical initial values, solve via algebraic ratios.
- Isolate the scaling coefficient. Do not assign arbitrary values to unstated variables.

## 3. STATE BOUNDARY LATCHING
- IF disconnected from battery: Q = constant. Use U = Q**2 / (2 * C).
- IF connected to battery: V = constant. Use U = 0.5 * C * V**2.

## 4. CONVERSION & PRECISION RULES
- Do not add numeric metric conversion multipliers within python_code.
- Process input values natively. Metric conversions must occur in preprocessing or postprocessing.
- BANNED FUNCTIONS: round(), .evalf(precision).