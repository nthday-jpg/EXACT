# Router Configuration

## Domain Options
Physics domains:
- electrostatic_force
- electrostatic_field
- ac_impedance
- resonance
- frequency_scaling
- electromagnetism
- oscillation_energy
- circuit_power
- capacitance_and_energy
- experimental_physics

Reasoning domains:
- spatial_topology
- coordinate_geometry
- vector_semantics
- qualitative_reasoning
- symbolic_derivation
- proportional_scaling
- error_analysis

## Domain Selection Rules

### experimental_physics
Use when: Experimental measurements, trial data sets, absolute or relative uncertainties, instrument tolerances, or duplicate measurement values.

### capacitance_and_energy
Use when: Parallel-plate configurations, dielectric replacement/materials, charge storage (Q), electrostatic potential energy storage, plate area (S), and separation (d).

### error_analysis
Use when: Random error, percentage relative error, standard deviation, range-based uncertainty, or error propagation.

### proportional_scaling
Use when: Qualitative ratio problems, "how does X change if Y doubles", behavioral scaling trends without absolute numerical values, or before/after fractional adjustments.

### electrostatic_force
Use when: Coulomb interactions, electric force, attractive/repulsive forces, or point charge mechanics.

### electrostatic_field
Use when: Electric field intensity (E), flux lines, field distribution, or co-located vertex field calculations.

### ac_impedance
Use when: RLC alternating current series circuits, phasor geometry, component voltages (VR, VL, VC), or phase angle calculations.

### resonance
Use when: Reactance cancellations (XL == XC), maximum AC current states, zero phase angles, or resonant frequency calculations.

### frequency_scaling
Use when: System frequency changes, omega transformations, or non-linear adjustments to capacitive/inductive reactance.

### electromagnetism
Use when: Magnetic flux, flux linkage, inductive EMF, self-inductance (L), solenoids, or magnetic energy density.

### oscillation_energy
Use when: LC circuit energy conservation, continuous exchange between electric and magnetic energies, or fraction of maximum energy states.

### circuit_power
Use when: DC power, AC average power, power factors, Joule heating, or parallel multi-branch entity calculations.

### spatial_topology
Use when: 1D linear charge positions, zero-point field cancellation coordinates, segment boundaries, or collinear linearity arrays.

### coordinate_geometry
Use when: Right-angle, equilateral, or general triangles requiring explicit 2D spatial coordinate mapping loops.

### vector_semantics
Use when: 2D directional quantities, matrix norm calculations, vector component decompositions, or spatial aggregation.

### qualitative_reasoning
Use when: Purely conceptual/descriptive answers, direction trends (increase/decrease), or binary Yes/No confirmations.

### symbolic_derivation
Use when: Requests algebraic formulas, expressions, equations, or string relationships instead of numerical answers.

## Question Types
- Numerical
- Formula
- Qualitative

## Question Type Rules

### Numerical
Use when: Problem explicitly asks for a final concrete numerical value, numeric magnitude calculation, or specific scalar quantity containing physical engineering units.
- BANNED: Do not use for relative trend adjustments or qualitative fractional behavior statements.

### Formula
Use when: Problem asks for an equation, algebraic formula, symbolic relation, variable derivation, or expression string instead of a number.

### Qualitative
Use when: Problem asks what happens conceptually, predicts trend shifts ("doubles", "halves", "quadruples"), requires directional responses ("increases", "decreases"), or asks for binary confirmation ("Yes", "No").
- MANDATORY: All proportional scaling ratio questions that lack absolute starting values must be classified under this type.

## Additional Field
### multi_state
Set true when problem contains: before/after states, transformed systems, frequency changes, or state transitions. Otherwise set false.

## OUTPUT FORMAT
{
  "domains": ["domain1", "domain2"],
  "question_type": "Numerical",
  "multi_state": true
}