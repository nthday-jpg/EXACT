<PHYSICS_LOGIC_HEURISTICS>
FIRST identify the problem type:
- electrostatic force
- electric field
- geometry
- resonance
- AC impedance
- frequency scaling
- vector resultant
- measurement/error

Then apply only the relevant rules.

## 1. GEOMETRIC ANCHORING
  - Anchor:
    - A = (0,0)
    - B = (ab, 0)

  - Third point:
    `xc = (ac**2 + ab**2 - bc**2) / (2 * ab)`
    `yc = sp.sqrt(sp.Max(0, ac**2 - xc**2))`
  - ISOSCELES RIGHT TRIANGLE:
    - A = (0,0)
    - B = (L,0)
    - C = (0,L)
  - PERPENDICULAR BISECTOR:
  If M lies on the perpendicular bisector of AB and is h away from AB:
    `M = (ab/2, h)`

## 2. ELECTRIC FORCE & FIELD
  - DIRECT FORCE:
    Compute force directly.
    Do not compute intermediate electric field first.
  - FORCE VECTORS:
    `F_vec = sum((ke * q_target * q_i * d_i) / r_i**3)`
  - FIELD VECTORS:
    `E_vec = sum((ke * q_i * d_i) / r_i**3)`
  - VECTOR DIRECTION:
    `d_i = target - source`
  - Component-vector form uses `r**3` in the denominator.
  - MAGNITUDE:
    `F_mag = sp.sqrt(Fx_total**2 + Fy_total**2)`
    `E_mag = sp.sqrt(Ex_total**2 + Ey_total**2)`
  - MIDPOINT SYMMETRY:  
    If the target lies at the midpoint between two charges on the same line,
    use 1D vector logic with sign determined by dx.
  - SELF SOURCE EXCLUSION:
    Never compute force or field contributions from the target charge itself.

## 3. AC PHASE & IMPEDANCE.
  - 90 DEGREE PHASE:
    `tan(phi_AM) * tan(phi_MB) = -1`
  - TANGENT:
    `tan(phi) = (XL - XC) / R`
  - Local segment forms:
    `tan(phi_AM) = (XL_AM - XC_AM) / R1`
    `tan(phi_MB) = (XL_MB - XC_MB) / R2`
  - Use:
    `sp.Eq(tan_phi_AM * tan_phi_MB, -1)`
  - SERIES VOLTAGE:
    `U_total**2 = (V_R_total)**2 + (V_L_total - V_C_total)**2`
  - Orthogonal segment voltages:
    `U_total**2 = U_AM**2 + U_MB**2`
  - SEGMENT VOLTAGE:
    `U_segment = I_rms * Z_segment`
  - SEGMENT IMPEDANCE:
    `Z_segment = sqrt(R_segment**2 + (XL_segment - XC_segment)**2)`
  - Resonance cancels TOTAL reactance only,
    not segment reactance.
  - TOTAL IMPEDANCE:
    `Z = sp.sqrt(R**2 + (XL - XC)**2)`

  - Resonance cancels only TOTAL reactance, not segment reactance.

## 4. VECTOR RESULTANTS (COW LAW)
  `R = sp.sqrt(A**2 + B**2 + 2*A*B*sp.cos(sp.pi * sp.Float(theta)/180))`

## 5. RESONANCE
  - Resonance:
    `XL = XC`
  - At resonance:
    `Z = total resistance only`
  - Angular frequency:
    `omega = 1/sp.sqrt(L*C)`
  - Ordinary frequency:
    `f = 1/(2*pi*sqrt(L*C))`
  - Relation:
    `omega = 2*pi*f`
  - Use resonance relations to solve unknown L, C, or omega BEFORE numerical evaluation.
  - 
## 6. SYMBOLIC VS NUMERIC.
  - Numerical questions:
    resolve all symbols before evaluation.
  - Formula questions:
    return the formula string inside `ans`.
  - Qualitative questions:
    return the exact text answer inside `ans`.

## 7. AC FREQUENCY SCALING & MULTI-STATE.
  - MULTI-STATE VARIABLES:
    Always define separate explicit variables for distinct physical states (e.g., `XL_0` vs `XL_new`).
    Never reuse the same base variable across different frequencies.
  - SCALING RELATION:
    If: `omega_new = k * omega_0`
    Then:
    `XL_new = k * XL_0`
    `XC_new = XC_0 / k`
  - Do not assume the initial state is resonance unless explicitly stated.

[FEW-SHOT EXAMPLE]
User: Two point charges, q1 = 4e-6 C and q2 = -6.4e-6 C, are placed at points A and B, separated by 0.2 m in air. Determine the magnitude of the electric force acting on q3 = -5e-8 C placed at point C, given that AC = 0.12 m and BC = 0.16 m.
Assistant:
{
  "thought": "Geometry anchoring required. q1@A(0,0), q2@B(0.2,0), q3@C(xc,yc). q1 and q2 are sources, q3 is the target. Compute force directly using Coulomb vector components.",
  "physics_analysis": [
    "q1=4e-6 C at A(0,0)",
    "q2=-6.4e-6 C at B(0.2,0)",
    "q3=-5e-8 C at C(xc,yc)",
    "ke=9e9",
    "Target unit: N"
  ],
  "algebraic_reasoning": [
    "Compute xc and yc",
    "Compute force vectors from q1 and q2 acting on q3",
    "Sum Fx and Fy",
    "Compute force magnitude"
  ],
  "python_code": "import sympy as sp; ke = sp.Float('9e9'); ab = sp.Float('0.2'); ac = sp.Float('0.12'); bc = sp.Float('0.16'); xc = (ac**2 + ab**2 - bc**2) / (2 * ab); yc = sp.sqrt(sp.Max(0, ac**2 - xc**2)); q1, q2, q3 = sp.Float('4e-6'), sp.Float('-6.4e-6'), sp.Float('-5e-8'); dx1 = xc - sp.Float('0'); dy1 = yc - sp.Float('0'); r1 = sp.sqrt(dx1**2 + dy1**2); Fx1 = (ke * q3 * q1 * dx1) / r1**3; Fy1 = (ke * q3 * q1 * dy1) / r1**3; dx2 = xc - ab; dy2 = yc - sp.Float('0'); r2 = sp.sqrt(dx2**2 + dy2**2); Fx2 = (ke * q3 * q2 * dx2) / r2**3; Fy2 = (ke * q3 * q2 * dy2) / r2**3; Fx_total = Fx1 + Fx2; Fy_total = Fy1 + Fy2; F_mag = sp.sqrt(Fx_total**2 + Fy_total**2); ans = [float(F_mag.evalf())]; unit = ['N']",
  "json_terminated": true
}

User: A circuit segment AB consists of two series parts. The first part (AM) has R1 = 30 Ω in series with a capacitor C. The second part (MB) has R2 = 70 Ω in series with an inductor L. The circuit satisfies LC*omega^2 = 1. An RMS voltage U = 100 V is applied across AB. The voltage uAM is 90 degrees out of phase with uMB. What is the RMS voltage across segment MB?
Assistant:
{
  "thought": "Resonance condition gives XL = XC. Segment voltages are 90 degrees out of phase, so tan(phi_AM) * tan(phi_MB) = -1. Segment reactances must be preserved when computing U_MB.",
  "physics_analysis": [
    "R1 = 30 ohm",
    "R2 = 70 ohm",
    "U = 100 V",
    "Resonance constraint: XL = XC",
    "Phase constraint: tan(phi_AM) * tan(phi_MB) = -1",
    "Target unit: V"
  ],
  "algebraic_reasoning": [
    "Express local tangent relations",
    "Apply phase constraint",
    "Use resonance relation XL = XC",
    "Compute total current",
    "Compute Z_MB",
    "Compute U_MB"
  ],
  "python_code": "import sympy as sp; R1 = sp.Float('30'); R2 = sp.Float('70'); U = sp.Float('100'); XL, XC = sp.symbols('XL XC', real=True, positive=True); tan_am = -XC / R1; tan_mb = XL / R2; eq_phase = sp.Eq(tan_am * tan_mb, sp.Float('-1')); eq_res = sp.Eq(XL, XC); sol = sp.solve([eq_phase, eq_res], (XL, XC), dict=True); sol = [s for s in sol if s[XL].is_real and s[XL] > 0]; xl_val = sol[0][XL]; Z_total = R1 + R2; I_rms = U / Z_total; Z_MB = sp.sqrt(R2**2 + xl_val**2); U_MB = I_rms * Z_MB; ans = [float(U_MB.evalf())]; unit = ['V']",
  "json_terminated": true
}
</PHYSICS_LOGIC_HEURISTICS>