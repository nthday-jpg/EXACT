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

## 5. CO-LOCATED TARGET EXCLUSION (SELF-FIELD / SELF-FORCE INTEGRITY)
- If a problem states that multiple source charges occupy the vertices of a geometric figure (such as a triangle or square) and asks for the net electric field or force at one of those specific vertices, you MUST apply the self-exclusion principle.
- A point charge cannot exert an interaction field or force upon its own coordinate position. 
- Identify the target vertex coordinate and completely exclude the charge residing at that coordinate from your list of active field/force sources. 
- For an isosceles right triangle of leg length 'a' with identical charges 'q' at all three vertices, the field at the right-angle vertex is generated EXCLUSIVELY by the two leg charges. Since they act along mutually perpendicular axes relative to the origin, the exact execution line must resolve to:
  E1 = ke * q / a**2; E_net = sp.sqrt(E1**2 + E1**2) -> sp.sqrt(sp.Float('2')) * E1
- Never add ghost scaling terms or include the target coordinate charge as an active source vector.