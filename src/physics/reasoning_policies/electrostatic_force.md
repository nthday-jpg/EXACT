# electrostatic_force.md

## 1. ROLE ASSIGNMENT & ATTENUATION
- Explicitly separate source charges from the target charge. Compute forces acting ON the target charge only.
- Force decays with distance squared: F = ke * sp.Abs(q1 * q2) / r**2. Never omit the exponent.
- Coulomb constant: ke = sp.Float('9e9')
- Vacuum Permittivity: epsilon_0 = sp.Float('1.0') / (sp.Float('4') * sp.pi * ke)

## 2. FORCE SIGN SEMANTICS & ORIENTATION
- Determine interaction type: Like charges repel; opposite charges attract.
- Repulsive (Like signs): Force vector points from Source to Target.
- Attractive (Opposite signs): Force vector points from Target to Source.

## 3. MANDATORY MATRIX ANCHORING & CONCRETE BINDING
- Anchor the target calculation charge strictly at the origin: Target_Pos = sp.Matrix([sp.Float('0'), sp.Float('0')])
- Map source positions strictly into explicitly named variables (e.g., Pos_A, Pos_B).
- Execute sequential vector evaluation manually. Never wrap vector extraction in custom dynamic functions or use sp.sign() scaling. Compute exactly via:
  d_vec1 = Target_Pos - Pos_A (if repulsive) else Pos_A - Target_Pos
  r1 = d_vec1.norm()
  u_vec1 = d_vec1 * (sp.Float('1.0') / r1)
  F_vec1 = (ke * sp.Abs(q1 * q0) / r1**2) * u_vec1
- Repeat sequentially for all source points (F_vec2, F_vec3, etc.).
- Total vector composition must be evaluated using: F_total = F_vec1 + F_vec2 + ...
- Compute final resultant scalar magnitude strictly via: F_mag = F_total.norm()

## 4. AGGREGATION & MULTI-CHARGE SYSTEMS
- Decompose force vectors into orthogonal components, sum X and Y groups separately, and calculate the final resultant scalar magnitude using: F_mag = sp.Abs(sp.sqrt(Fx_total**2 + Fy_total**2))
- SELF FORCE: A charge cannot exert a force on itself. Never include the target charge as a source.

## 5. CAPACITOR SYSTEM COUPLING & BATTERY WORK
- Parallel Plate Capacitance: C = epsilon_0 * S / d
- Force between parallel plates: F = (Q**2) / (sp.Float('2') * epsilon_0 * S)
- ENERGY VS WORK BOUNDARY:
  - IF calculating the change in stored electrostatic energy inside the capacitor, use: Delta_E = sp.Float('0.5') * U**2 * (C_final - C_init)
  - IF calculating the work supplied or absorbed by the external voltage source/battery, use: Delta_W = U**2 * (C_final - C_init). Never include the 0.5 factor for battery work computations.