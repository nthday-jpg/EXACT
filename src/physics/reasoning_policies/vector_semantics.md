# vector_semantics.md

## 1. RESOLUTION
- Decompose vectors into orthogonal components (X, Y), sum them separately, and compute resultant magnitude at the end.
- Matrix Division Rule: Do not divide a matrix object directly by a scalar magnitude (e.g., matrix / r is banned). Multiply by the scalar inverse instead.
- Syntax Template: `u_vec = d_vec * (sp.Float('1.0') / r)`

## 2. AGGREGATION & MAGNITUDE
- Vx_total = sum(Vx)
- Vy_total = sum(Vy)
- V_mag = sp.Abs(sp.sqrt(Vx_total**2 + Vy_total**2))

## 3. COORDINATE MAPPING
- Anchor the calculation target vertex directly at the coordinate origin: `Target_Vertex = sp.Matrix([sp.Float('0'), sp.Float('0')])`
- Map source positions relative to this origin. Displacement vectors must point from source to target origin.

## 4. PRECISION LOCK
- BANNED: round(), internal float() transformations, or precision-bound .evalf(precision) expressions mid-calculation.
- Assign full precision values directly to the output array.