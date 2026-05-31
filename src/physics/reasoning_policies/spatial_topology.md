# spatial_topology.md

## 1. LINEAR STATE TOPOLOGY (ZERO-POINTS)
When finding the coordinate where a physical quantity cancels along a 1D line between point A (at 0) and point B (at d):
- REINFORCING STATES: If the physical contributions from A and B align their vector directions internally, the zero-point CANNOT lie between them. It must lie on the exterior.
  - If Magnitude(A) > Magnitude(B): The zero-point is past B. Coordinate: x > d. Distance to B is (x - d).
  - If Magnitude(A) < Magnitude(B): The zero-point is past A. Coordinate: x < 0. Distance to B is (d - x).
- OPPOSING STATES: If the physical contributions naturally cancel inside the boundary, the zero-point lies strictly between them. Coordinate: 0 < x < d. Distance to B is (d - x).
- AMBIGUOUS POINT POSITIONING: If a third point (C) is introduced along a line segment AB without explicit text defining it as the midpoint or specifying its exact coordinate boundary, never assume or guess it is a midpoint. Validate the question's text constraints against existing force fields first to see if it resides on the segment exterior.

## 2. COLLINEAR LINEARITY
- Segment Interior: r1 + r2 == AB -> The point is strictly between coordinates A and B.
- Segment Exterior: abs(r1 - r2) == AB -> The point is outside the segment. Never apply interior spatial configurations to exterior coordinate logic.

## 3. PERPENDICULAR BISECTOR
- If distance PA == PB, the point P shares the coordinate midpoint along that axis: X_P = (X_A + X_B) / 2.
- The offset orthogonal coordinate component forms a right triangle: r**2 = (AB / 2)**2 + y**2.

## 4. MIDPOINT SYMMETRY & INVERSE SQUARE FORCE
- Equal physical magnitudes across a symmetric midpoint do NOT inherently imply cancellation. Always analyze property signs explicitly.
- MANDATORY ATTENUATION LAW: Force and field interactions across spatial topologies must always decay with distance squared. Never omit the exponent: always use r**2 for fields (E = ke * q / r**2) and forces (F = ke * q1 * q2 / r**2).