# coordinate_geometry.md

## 1. STANDARD LINE
A = (0,0)
B = (ab,0)

## 2. GENERAL TRIANGLE
xc = (ac**2 + ab**2 - bc**2)/(2*ab)
yc = sqrt(ac**2 - xc**2)
C = (xc,yc)

## 3. EQUILATERAL TRIANGLE
A = (0,0)
B = (a,0)
C = (a/2, a*sqrt(3)/2)

## 4. RIGHT ISOSCELES TRIANGLE
A = (0,0)
B = (L,0)
C = (0,L)

## 5. PERPENDICULAR BISECTOR
M = (ab/2, h)

## 6. COLLINEAR SPECIAL CASE
If all points are collinear:
- use 1D signed coordinates
- do not introduce y-components

## 7. VALIDATION
After assigning coordinates:
verify all:
- distances
- midpoint conditions
- equal-distance constraints
- perpendicular constraints
Reject invalid coordinate systems.

## 8. VECTOR DERIVATION FROM COORDINATES
Given source point S=(xs, ys) and target point T=(xt, yt):
1. Displacement vector: d_vec = Matrix([xt - xs, yt - ys])
2. Distance: r = d_vec.norm()
3. Unit direction vector: u_hat = d_vec / r
4. Vector quantity: V_vec = V_magnitude * u_hat
Never manually guess components; always use the structural unit vector u_hat.