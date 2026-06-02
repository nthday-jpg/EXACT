# coordinate_geometry.md

## 1. STANDARD LINE
A = (sp.Float('0'), sp.Float('0'))
B = (ab, sp.Float('0'))

## 2. GENERAL TRIANGLE
xc = (ac**2 + ab**2 - bc**2) / (sp.Float('2') * ab)
yc = sp.sqrt(ac**2 - xc**2)
C = (xc, yc)

## 3. EQUILATERAL TRIANGLE
A = (sp.Float('0'), sp.Float('0'))
B = (a, sp.Float('0'))
C = (a / sp.Float('2'), a * sp.sqrt(sp.Float('3')) / sp.Float('2'))

## 4.a RIGHT-ANGLED TRIANGLE EXPLICIT BINDING (PYTHAGOREAN TRIPLE GUARD)
- Before applying any general algebraic projection formula (Law of Cosines) for an oblique triangle, check if the given side lengths (e.g., 6, 8, 10 or 12, 16, 20) satisfy the Pythagorean theorem: leg1**2 + leg2**2 == hypotenuse**2.
- If a right-angle configuration is verified, you MUST bypass general projection rules and anchor the right-angle vertex directly at the origin (sp.Float('0'), sp.Float('0')).
- Map the two perpendicular legs cleanly along the absolute, flat 1D coordinate axes:
  - Right-Angle Vertex (Target): Matrix([0, 0])
  - Source 1 (Leg 1): Matrix([leg1, 0])
  - Source 2 (Leg 2): Matrix([0, leg2])
- This eliminates floating-point projection tilt and maintains rigid component geometry.

## 5. PERPENDICULAR BISECTOR
- M = (ab / sp.Float('2'), h)
- Maintain absolute symbolic precision throughout the calculation.
- BANNED: internal float() conversions or round() calls mid-execution (e.g., `r = sp.Float(float(...))` is illegal). Scaling occurs in preprocessing or postprocessing.

## 6. COLLINEAR SPECIAL CASE (MANDATORY 2D MAPPING)
If all points are collinear:
- Map the target calculation point strictly to the 2D origin coordinate: (sp.Float('0'), sp.Float('0'))
- Map all relative source coordinates directly along the X-axis: (x_val, sp.Float('0'))
- Do not omit the y-coordinate field; anchor it explicitly to sp.Float('0') to keep matrix dimensionality uniform

## 7. VALIDATION
After assigning coordinates, verify all:
- distances
- midpoint conditions
- equal-distance constraints
- perpendicular constraints
Reject invalid coordinate systems.

## 8. VECTOR DERIVATION FROM COORDINATES
Given source point S=(xs, ys) and target point T=(xt, yt):
1. Displacement vector: d_vec = sp.Matrix([xt - xs, yt - ys])
2. Distance: r = d_vec.norm()
3. Unit direction vector: u_hat = d_vec * (sp.Float('1.0') / r)
4. Vector quantity: V_vec = V_magnitude * u_hat
Never manually guess components; always use the structural unit vector u_hat.