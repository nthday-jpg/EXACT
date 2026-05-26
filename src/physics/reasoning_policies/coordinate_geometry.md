##1. STANDARD LINE
A = (0,0)
B = (ab,0)

##2. GENERAL TRIANGLE
xc = (ac**2 + ab**2 - bc**2)/(2*ab)

yc = sqrt(ac**2 - xc**2)

C = (xc,yc)

##3. EQUILATERAL TRIANGLE
A = (0,0)
B = (a,0)
C = (a/2, a*sqrt(3)/2)

##4. RIGHT ISOSCELES TRIANGLE
A = (0,0)
B = (L,0)
C = (0,L)

##5. PERPENDICULAR BISECTOR
M = (ab/2, h)

##6. COLLINEAR SPECIAL CASE
If all points are collinear:
- use 1D signed coordinates
- do not introduce y-components

##7. VALIDATION
After assigning coordinates:
verify all:
- distances
- midpoint conditions
- equal-distance constraints
- perpendicular constraints

Reject invalid coordinate systems.