# oscillation_energy.md

## 1. EQUATIONS
- W_total = WC + WL
- WL = W_total - WC

## 2. BOUNDARY CONDITIONS
- Electric and magnetic energies exchange continuously.
- Track variables for target benchmarks: maximum, minimum, zero, increasing, decreasing.

## 3. SCALING & PERCENTAGE RULE
- Do not multiply ratios by sp.Float('100') inside python_code to calculate percentages.
- Assign the raw fraction or float ratio directly to ans. 
- All percentage scaling transforms must occur in preprocessing or postprocessing layers.