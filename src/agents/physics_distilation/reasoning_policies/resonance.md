# resonance.md

## 1. RESONANCE CONDITION
XL = XC

## 2. RESONANCE EFFECT
At resonance: total impedance is purely resistive, current is maximal, and phase angle = 0.

## 3. TOTAL REACTANCE
Only TOTAL reactance cancels. Segment reactances remain nonzero.

## 4. FREQUENCY RELATIONS
omega = 1 / sqrt(L * C)
f = 1 / (2 * pi * sqrt(L * C))
omega = 2 * pi * f

## 5. SOLVING ORDER
1. Apply resonance condition -> 2. Simplify physics qualitatively -> 3. Solve symbolically -> 4. Evaluate numerically.

## 6. RESONANCE DETECTION
Frequency scaling may create resonance implicitly. Check transformed reactances BEFORE solving.

## 7. QUALITATIVE VERIFICATION OVERRIDE
- If the question asks a binary verification question (e.g., "Will resonance occur at f=...?"), do NOT output the calculated numeric resonant frequency as your final answer string.
- Evaluate the conditional check inside your thought process, but NEVER use a strict threshold like 1e-9. Real-world textbook values use rounded constants.
- In your Python condition, evaluate resonance as True if the given frequency is within a 1% relative tolerance buffer of the calculated peak frequency:
  is_resonant = abs(f_given - f_res) / f_res < 0.01
  ans = ['Yes'] if is_resonant else ['No']; unit = ['-']