# error_analysis.md

## 1. RANDOM ERROR RESOLUTION (RANGE RULE)
- For small sample trial sets (typically N < 10), random error is defined as half the total span of the data set. 
- You MUST bypass traditional population standard deviation computations unless the question explicitly commands the use of standard deviation.
- Calculate random uncertainty using the maximum and minimum values exactly via:
  `random_error = (max(measurements) - min(measurements)) / sp.Float('2')`

## 2. RELATIVE & PERCENTAGE ERROR SEMANTICS
- Relative Error ($e_r$) is the absolute uncertainty ($\Delta x$) divided by the nominal measured or mean value ($x$).
- Percentage Relative Error ($\% e_r$) scales this ratio by 100:
  `perc_err = (delta_x / x_nominal) * sp.Float('100')`
- Never embed rounding logic like `round()` or `.evalf(2)` inside the python code string. Let the post-processing engine handle decimal truncations.

## 3. OUTPUT SPECIFICATION
- The tracking variable `ans` must always be a float cast of the final evaluated calculation: `ans = [float(perc_err.evalf())]`.