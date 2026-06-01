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
- symbolic_derivation

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
- AC circuits & phasor geometry (RMS voltage/current, impedance, RLC resonance combinations)

### qualitative_reasoning
Use when:
- conceptual explanation
- trend/behavior
- increase/decrease
- yes/no conceptual reasoning
- qualitative relationships
- "depends on which quantities/factors..."
- yes/no conceptual reasoning

### symbolic_derivation
Use when:
- "Find the formula for..."
- "Express X in terms of Y..."
- "Derive the relationship equation..."
- Answer format must be a raw symbolic equation string instead of a numerical value.

## Multi-Domain Rules

Questions can and should require multiple domains where applicable.

Examples of complete responses:

### Example 1: Electrostatic triangle force
{"domains": ["electrostatic_force", "coordinate_geometry", "vector_semantics"], "question_type": "Numerical", "multi_state": false}

### Example 2: Electric field at midpoint
{"domains": ["electrostatic_field", "spatial_topology", "vector_semantics"], "question_type": "Numerical", "multi_state": false}

### Example 3: Resonance after frequency doubling
{"domains": ["frequency_scaling", "resonance", "ac_impedance"], "question_type": "Numerical", "multi_state": true}

### Example 4: AC power at resonance
{"domains": ["circuit_power", "resonance", "ac_impedance"], "question_type": "Numerical", "multi_state": false}

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
Set true when problem contains:
- before/after states
- transformed systems
- frequency changes
- state transitions
Otherwise set false.

## OUTPUT FORMAT
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
- Output one valid JSON object only.
- No markdown.
- No explanations.
- No chain-of-thought. 