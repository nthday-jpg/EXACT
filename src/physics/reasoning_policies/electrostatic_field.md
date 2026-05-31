# electrostatic_field.md

## 1. FIELD DEFINITION & INVERSE SQUARE LAW
- Electric field drops off with distance squared: E = ke * q / r**2. Never drop the exponent during coding.
- Standard unit: V/m | Coulomb constant: ke = sp.Float('9e9').

## 2. VECTOR ORIENTATION & DIRECTION
- Direction matches the force acting on a positive hypothetical test charge.
- Positive source: Field vector points away from the source position.
- Negative source: Field vector points directly toward the source position.

## 3. VECTOR IMPLEMENTATION & ORIGIN ANCHOR
- To eliminate manual sign guessing errors, anchor your evaluation target point strictly at the coordinate origin: Target_Pos = sp.Matrix([sp.Float('0'), sp.Float('0')]).
- Define source positions relative to this origin. Compute the field vector safely using:
  d_vec = Target_Pos - Source_Pos (For positive source) or Source_Pos - Target_Pos (For negative source)
  r = d_vec.norm()
  u_vec = d_vec * (sp.Float('1.0') / r)
  E_vec = (ke * q_source / r**2) * u_vec

## 4. AGGREGATION & MIDPOINTS
- Never add or subtract raw scalar field magnitudes directly unless sources are perfectly collinear. 
- Opposing charges on either side of a midpoint reinforce—they do not cancel. Decompose into orthogonal components, sum X and Y separately, and resolve the final magnitude via sp.Abs(sp.sqrt(Ex_total**2 + Ey_total**2)).