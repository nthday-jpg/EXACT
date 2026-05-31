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

## 4. RIGHT ISOSCELES TRIANGLE
A = (sp.Float('0'), sp.Float('0'))
B = (L, sp.Float('0'))
C = (sp.Float('0'), L)

## 5. PERPENDICULAR BISECTOR
- M = (ab / sp.Float('2'), h)
- For calculations involving distances to a perpendicular bisector, explicitly evaluate the hypotenuse distance numerically: r = sp.Float(float(sp.sqrt((ab/2)**2 + h**2)))
- Do not pass raw algebraic radical combinations downstream into matrix computations.

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