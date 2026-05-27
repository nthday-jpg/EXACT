# electrostatic_force.md

## 1. ROLE ASSIGNMENT
Explicitly define source charges and target charge. Compute force ON target only.

## 2. FORCE SIGN SEMANTICS
Determine interaction type: attraction or repulsion. Then construct unit vector accordingly.

## 3. FORCE VECTOR
1. Compute scalar magnitude: F = ke * abs(q_source * q_target) / r**2
2. Determine interaction: like charges repel, opposite charges attract.
3. Construct unit direction vector explicitly.
4. Multiply: F_vec = F * u_hat

## 4. FORCE PIPELINE
1. Assign coordinates -> 2. Compute displacement vectors -> 3. Determine directions -> 4. Compute vector components -> 5. Sum vectors -> 6. Compute magnitude.

## 5. MIDPOINT CASES
Do not assume cancellation from symmetry alone. Opposite charges at midpoint often reinforce.

## 6. SELF FORCE
Never compute self-force.

## 7. CAPACITANCE AND CONSTANTS
- Coulomb constant: ke = 9e9
- Vacuum Permittivity: epsilon_0 = 1 / (4 * sp.pi * ke)
- Parallel Plate Capacitance: C = epsilon_0 * S / d
- Force between plates: F = (Q**2) / (2 * epsilon_0 * S)
