# spatial_vector_geometry.md

## 1. UNIFIED 2D COORDINATE MAPPING & BOUNDARY GUARDS
- **Target Anchoring:** Always map the target calculation point strictly to the 2D origin: `Target_Vertex = sp.Matrix([sp.Float('0'), sp.Float('0')])`. Map all source positions relative to this origin.
- **Case A: Collinear Special Case (1D Lineup):**
  - If points are collinear, map all relative source coordinates directly along the X-axis: `(x_val, sp.Float('0'))`. Do not omit the Y-coordinate field; anchor it explicitly to keep matrix dimensionality uniform.
  - *Segment Interior Guard:* Verified when `r1 + r2 == AB`. 
  - *Segment Exterior Guard:* Verified when `abs(r1 - r2) == AB`. Never apply interior spatial configurations to exterior coordinate logic.
  - *Ambiguous Point Positioning:* Never assume or guess a third point C is a midpoint along segment AB without text constraints.
- **Case B: Right-Angled Triangle (Pythagorean Triple Guard):**
  - Check if side lengths satisfy `leg1**2 + leg2**2 == hypotenuse**2`.
  - If verified, bypass general projection rules and anchor the right-angle vertex at `sp.Matrix([0, 0])`. Map legs cleanly along flat 1D axes: `Matrix([leg1, 0])` and `Matrix([0, leg2])`.
- **Case C: General Oblique Triangle:**
  - For non-right-angled layouts, calculate the exact projection coordinates along the X and Y axes using the algebraic expressions:
    `xc = (ac**2 + ab**2 - bc**2) / (sp.Float('2.0') * ab)`
    `yc = sp.sqrt(ac**2 - xc**2)`
- **Case E: Equilateral Triangle:**
  - For uniform three-sided layouts with side length `a`, assign coordinates strictly using:
    `A = sp.Matrix([sp.Float('0.0'), sp.Float('0.0')])`
    `B = sp.Matrix([a, sp.Float('0.0')])`
    `C = sp.Matrix([a / sp.Float('2.0'), a * sp.sqrt(sp.Float('3.0')) / sp.Float('2.0')])`
- **Case D: Perpendicular Bisector:**
  - If distance PA == PB, share the axis coordinate midpoint: X_P = (X_A + X_B) / 2. The offset orthogonal component forms M = (ab / 2, h) where r**2 = (AB / 2)**2 + y**2.
- **System Validation:** After assigning coordinates, strictly verify all distances, midpoints, equal-distance constraints, and perpendicular constraints. Reject invalid coordinate systems.

---

## 2. LINEAR STATE TOPOLOGY (ZERO-POINTS)
When solving for coordinates where a physical quantity cancels along a 1D line between point A (at 0) and point B (at d):
- **Opposing States:** If contributions naturally cancel inside the boundary, the zero-point lies strictly between them: 0 < x < d. Distance to B is (d - x).
- **Reinforcing States:** Contributions align directions internally; the zero-point must lie on the exterior (x < 0 or x > d):
  - If Magnitude(A) > Magnitude(B): Zero-point is past B (x > d). Distance to B is (x - d).
  - If Magnitude(A) < Magnitude(B): Zero-point is past A (x < 0). Distance to B is (d - x).

---

## 3. VECTOR DERIVATION, ATTENUATION, & AGGREGATION
- **Displacement Vectors:** Must point directly from source S=(xs, ys) to target origin T=(xt, yt):
  `d_vec = sp.Matrix([xt - xs, yt - ys])`
- **Distance Magnitude:** Compute scalar distance using `r = d_vec.norm()`.
- **Mandatory Attenuation Law:** Force and field interactions must decay with distance squared (r**2). Always use explicit exponents: E = k_e * q / r**2 and F = k_e * q_1 * q_2 / r**2. Equal magnitudes across a symmetric midpoint do not inherently imply vector cancellation.
- **Matrix Division Rule:** Do not divide a matrix object directly by a scalar magnitude (e.g., `matrix / r` is banned). Multiply by the scalar inverse instead using the following strict template:
  `u_hat = d_vec * (sp.Float('1.0') / r)`
- **Vector Quantities:** Construct using structural unit vectors: `V_vec = V_magnitude * u_hat`. Do not manually guess components.
- **Orthogonal Aggregation:** Decompose vectors into orthogonal components (X, Y) and sum them separately:
  `Vx_total = sum(Vx)`
  `Vy_total = sum(Vy)`
- **Resultant Magnitude:** Compute the absolute total scalar magnitude at the very end of the execution block:
  `V_mag = sp.Abs(sp.sqrt(Vx_total**2 + Vy_total**2))`

---

## 4. PRECISION LOCK
- **Banned Syntax:** Do not use `round()`, internal `float()` transformations, or precision-bound `.evalf(precision)` expressions mid-calculation (e.g., `r = sp.Float(float(...))` is illegal). 
- **Execution:** Maintain absolute symbolic precision throughout the entire pipeline. Scaling must occur exclusively in preprocessing or postprocessing stages. Assign full precision symbolic or float values directly to the output array.