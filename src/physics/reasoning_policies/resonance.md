# resonance.md

## 1. CONDITIONS
- XL = XC
- omega = 1 / sp.sqrt(L * C)
- f = 1 / (sp.Float('2') * sp.pi * sp.sqrt(L * C))
- omega = sp.Float('2') * sp.pi * f

## 2. EFFECTS
- Total impedance is purely resistive. Current is maximal. Phase angle = 0.
- Only TOTAL reactance cancels. Segment reactances remain nonzero.

## 3. ORDER OF OPERATIONS
1. Apply resonance condition -> 2. Check transformed reactances -> 3. Evaluate target expression.

## 4. BINARY VERIFICATION OVERRIDE
- If the question asks a binary verification question ("Will resonance occur?"), ans must hold text, not a frequency float.
- Evaluate resonance as True if the given frequency is within a 1% relative tolerance buffer of the peak frequency.
- Code Template (No trailing semicolon):
  `is_resonant = sp.Abs(f_given - f_res) / f_res < sp.Float('0.01'); ans = ['Yes'] if is_resonant else ['No']; unit = ['-']`