## 1. VECTOR INVARIANT & MATRIX RESOLUTION
- Directional quantities are vectors. Never add scalar magnitudes directly unless vectors are perfectly collinear.
- Decompose vectors into orthogonal components (X, Y), sum them separately, and compute the absolute resultant magnitude at the very end.
- MATRIX DIVISION RULE: Never divide a scalar directly by a spatial position matrix. Always divide by its norm magnitude.
- Use SymPy Matrix transformations to prevent manual trigonometry and sign errors:
  `d_vec = target_pos - source_pos` (Direction is always Source to Target)
  `r = d_vec.norm()`
  `u_vec = d_vec / r`
  `V_vec = scalar_magnitude * u_vec`
- AC CIRCUIT PHASOR INVARIANT: AC voltages (V_rms), currents (I_rms), reactances (X_L, X_C), and impedances (Z) are 2D vectors (phasors). 
  - Never combine AC series/parallel component values using direct scalar addition unless they are explicitly in phase.
  - Orthogonal phasor series combinations (such as Resistor-Capacitor V_RC or Resistor-Inductor V_RL) must be resolved using right-triangle vector components: V_RC = sp.sqrt(V_R**2 + V_C**2).
- SOURCE FIELD DIRECTION RULE: When setting up a field vector (electric field, gravitational field) from a source point to a target point, true vector directions must be handled explicitly:
  - Positive Source / Repulsive: Vector points strictly from Source to Target (`d_vec = target_pos - source_pos`).
  - Negative Source / Attractive: Vector points strictly from Target to Source (`d_vec = source_pos - target_pos`).

## 2. COMPONENT AGGREGATION & MAGNITUDE
- Total directional sums must be explicitly aggregated across all contributing vector indices:
  `Vx_total = sum(Vx)`, `Vy_total = sum(Vy)`
- MAGNITUDE SCALAR INVARIANT: Final scalar magnitude evaluations must wrap the component sum inside absolute values to eliminate negative directional signs:
  `V_mag = sp.abs(sp.sqrt(Vx_total**2 + Vy_total**2))`

## 3. CANCELLATION CONDITIONS
- Equal magnitudes alone do not guarantee cancellation. Vector cancellation requires net X == 0 AND net Y == 0 simultaneously.

## 4. SIGNED SCALAR ADDITION
- Signed scalar arithmetic (direct addition/subtraction of raw values) is strictly reserved for perfectly collinear vectors operating along a single coordinate axis.