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

Reasoning domains:
- spatial_topology
- coordinate_geometry
- vector_semantics
- qualitative_reasoning

## Domain Selection Rules

### electrostatic_force
Use when:
- electric force
- Coulomb force
- attraction/repulsion
- force on a charge
- net force between charges

### electrostatic_field
Use when:
- electric field
- field intensity
- field at a point
- superposition of fields

### ac_impedance
Use when:
- impedance
- phase angle
- phasor voltage
- RMS voltage/current
- AC circuit analysis
- RLC circuits

### resonance
Use when:
- resonance
- resonant frequency
- XL = XC
- maximal current
- resonance behavior

### frequency_scaling
Use when:
- frequency changes
- doubled/halved frequency
- transformed reactance
- scaling relations
- before/after frequency states

### electromagnetism
Use when:
- magnetic flux
- inductance
- induced emf
- solenoid
- magnetic energy

### oscillation_energy
Use when:
- LC energy exchange
- capacitor energy
- inductor energy
- oscillation energy conservation

### circuit_power
Use when:
- electric power
- RMS power
- Joule heating
- power factor
- energy consumption

### spatial_topology
Use when:
- midpoint
- collinear points
- perpendicular bisector
- equal-distance constraints
- topology inference

### coordinate_geometry
Use when:
- coordinates required
- triangle reconstruction
- geometric anchoring
- distance reconstruction

### vector_semantics
Use when:
- vector decomposition
- force/field components
- cancellation analysis
- directional reasoning
- vector addition

### qualitative_reasoning
Use when:
- conceptual explanation
- trend/behavior
- increase/decrease
- yes/no conceptual reasoning
- qualitative relationships

## Multi-Domain Rules

Questions may require multiple domains.

Examples:

Electrostatic triangle force:
[
  "electrostatic_force",
  "coordinate_geometry",
  "vector_semantics"
]

Electric field at midpoint:
[
  "electrostatic_field",
  "spatial_topology",
  "vector_semantics"
]

Resonance after frequency doubling:
[
  "frequency_scaling",
  "resonance",
  "ac_impedance"
]

AC power at resonance:
[
  "circuit_power",
  "resonance",
  "ac_impedance"
]

## Question Types

- Numerical
- Formula
- Qualitative

## Question Type Rules

### Numerical
Use when:
- asks for numerical value
- asks for magnitude
- requires units

### Formula
Use when:
- asks for equation
- asks for symbolic relation
- asks for derivation

### Qualitative
Use when:
- asks what happens
- asks for explanation
- asks increase/decrease
- asks conceptual relationship

## Additional Field

### multi_state
Set:
true

when problem contains:
- before/after states
- transformed systems
- frequency changes
- state transitions

Otherwise:
false

## OUTPUT FORMAT

Return ONLY a single JSON object:

{
  "domains": ["domain1", "domain2"],
  "question_type": "Numerical",
  "multi_state": true
}

Rules:
- Multiple domains are allowed.
- Prefer specific domains over broad ones.
- Include reasoning domains if required for solving.
- Do not include irrelevant domains.
- Output valid JSON only.
- No markdown.
- No explanations.
- No chain-of-thought.