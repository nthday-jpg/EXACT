# vector_semantics.md

## 1. VECTOR INVARIANT & MATRIX RESOLUTION
- Directional quantities are vectors. Never add scalar magnitudes directly unless vectors are perfectly collinear.
- Decompose vectors into orthogonal components (X, Y), sum them separately, and compute the absolute resultant magnitude at the very end.
- MATRIX DIVISION RULE: Never divide a scalar directly by a spatial position matrix. Always divide by its norm magnitude.
- Use SymPy Matrix transformations to prevent manual trigonometry and sign errors:
  d_vec = target_pos - source_pos (Direction is always Source to Target)
  r = d_vec.norm()
  u_vec = d_vec * (sp.Float('1.0') / r)
  V_vec = scalar_magnitude * u_vec

## 2. COMPONENT AGGREGATION & MAGNITUDE
- Total directional sums must be explicitly aggregated across all contributing vector indices:
  Vx_total = sum(Vx), Vy_total = sum(Vy)
- MAGNITUDE SCALAR INVARIANT: Final scalar magnitude evaluations must wrap the component sum inside absolute values to eliminate negative directional signs:
  V_mag = sp.Abs(sp.sqrt(Vx_total**2 + Vy_total**2))

## 3. CANCELLATION CONDITIONS
- Equal magnitudes alone do not guarantee cancellation. Vector cancellation requires net X == 0 AND net Y == 0 simultaneously.

## 4. SIGNED SCALAR ADDITION
- Signed scalar arithmetic (direct addition/subtraction of raw values) is strictly reserved for perfectly collinear vectors operating along a single coordinate axis.

## 5. VECTOR IMPLEMENTATION GUARD
- NEVER mix raw Matrix calls without the namespace prefix; always use sp.Matrix().
- NEVER divide a sp.Matrix object by a scalar directly (e.g., d1 / r1). Instead, multiply the matrix by the scalar inverse: d1 * (sp.Float('1.0') / r1).

## 6. CANONICAL COORDINATE MAPPING
- To prevent sign errors in 2D spatial geometries (like right or equilateral triangles), you MUST anchor the target calculation vertex directly at the coordinate origin: Target_Vertex = sp.Matrix([sp.Float('0'), sp.Float('0')]).
- Map all other charge/source positions relative to this origin. Displacement direction vectors must point from source to target origin, completely eliminating manual sign assignment guessing.