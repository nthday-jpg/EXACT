# experimental_physics.md

## 1. DATA INPUT INTEGRITY
- Treat all raw inputs containing explicit uncertainty boundaries (e.g., ± 0.1) or discrete trial lists as exact structural values.
- Never strip trailing zeros from experimental measurements (e.g., preserve '12.0' exactly as written; do not truncate to '12' or '12.00') as they establish the measurement precision bounds.

## 2. NATIVE VALUE BINDING
- Bind the raw values directly into SymPy Float variables without scaling modifiers.
- All metric prefix conversions and unit translations must be handled entirely during post-processing to avoid floating-point tracking pollution inside the execution script.

## 3. TRIAL ARRAYS
- Store sequential measurement runs inside native Python lists wrapped in SymPy elements to allow index-based operations: `measurements = [sp.Float('x1'), sp.Float('x2'), ...]`.