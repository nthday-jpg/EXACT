##1. ROLE ASSIGNMENT
Explicitly define:
- source charges
- target charge

Compute force ON target only.

##2. FORCE SIGN SEMANTICS
Like charges:
- repel

Opposite charges:
- attract

Determine physical direction BEFORE algebra.

##3. FORCE VECTOR
F_vec = (k*q_source*q_target*d_vec)/r**3

##4. FORCE PIPELINE
1. Assign coordinates
2. Compute displacement vectors
3. Determine directions
4. Compute vector components
5. Sum vectors
6. Compute magnitude

##5. MIDPOINT CASES
Do not assume cancellation from symmetry alone.

Opposite charges at midpoint often reinforce.

##6. SELF FORCE
Never compute self-force.

##7. CONSTANT
Use:
k = 9e9

unless explicitly specified otherwise.