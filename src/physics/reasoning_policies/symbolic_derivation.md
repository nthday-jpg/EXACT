# symbolic_derivation.md

## 1. SYMBOLIC DERIVATION DETECTION
Detect questions that ask for an algebraic formula, expression, equation, or relationship string instead of a numerical value (e.g., "Express X in terms of...", "Find the formula for...").

## 2. REASONING PRIORITY
- Isolate the target variable algebraically on one side of the equation.
- Simplify expressions by combining like terms.
- Strictly maintain standard variable naming conventions given in the problem text.

## 3. OUTPUT STYLE (FORMULA ONLY)
- Never numerically evaluate symbols or substitute numerical constants unless explicitly told to do so.
- Do not add text explanations inside the answer string.
- The 'ans' variable inside 'python_code' must be a raw Python-compatible symbolic string enclosed in a list.
  Example: ans = ["(mu0 * N * I) / l"]; unit = ["-"]
- CODE EXECUTION GUARD: Do not attempt to use `sp.solve()` or create mathematical operations on division symbols (like `V/I`) inside the executable code. Simply assign the final symbolic string answer directly to the list: e.g., ans = ["1 / (omega * C)"]
  
## 4. CONSTANT vs SYMBOL RULE
If the problem names a constant with a letter (k, ke, ε₀, G), keep it as 
a named symbol in the formula output regardless of any numerical value stated 
in the problem. Only substitute numerically if the question explicitly asks 
for a numerical answer.
Bad:  ans = ["18000000000.0 * h * q / (a**2 + h**2)**(3/2)"]
Good: ans = ["2*k*q*h / (a**2 + h**2)**(3/2)"]

## 5. COMPUTATION MODE GUARD
- Case A — Formula is derivable directly from known physics laws: 
  assign the string directly. Do not call sp.solve().
  Example: ans = ["2*k*q*h / (a**2 + h**2)**(3/2)"]; unit = ["V/m"]
- Case B — Formula requires derivation (differentiation, solving): 
  use sp.diff() and sp.solve() freely, but the final result must be 
  converted to string: ans = [str(result)]. Never call float() or 
  .evalf() on the final symbolic result.
  Example: ans = [str(h_sol[0])]; unit = ["m"]