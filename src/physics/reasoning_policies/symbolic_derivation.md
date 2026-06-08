# symbolic_derivation.md

## 1. SYMBOLIC DERIVATION DETECTION
Identify questions asking for an algebraic formula, expression, equation, or relationship string instead of a numerical value (e.g., "Express X in terms of...", "Derive the expression for...").

## 2. MANDATORY SYMPY CHAIN
- **CRITICAL:** Hardcoding raw string shortcuts into the `ans` list is strictly BANNED (e.g., `ans = ["1 / (omega * C)"]`).
- All derivations must occur programmatically inside the `python_code` environment using SymPy (`import sympy as sp`).
- The final assignment to the `ans` block must always use string conversion over a computed SymPy object: `ans = [str(result)]` or `ans = [str(sp.simplify(result))]`.

## 3. REASONING PRIORITY
- **Symbol Declaration:** Declare all variables and constants using `sp.symbols(..., positive=True)` where physically applicable to enable clean algebraic reduction.
- **Algebraic Isolation:** Use `sp.solve()` or `sp.isolate()` programmatically to manipulate equations and isolate the target variable.
- **Simplification Guard:** Always run `sp.simplify()`, `sp.expand()`, or `sp.trigsimp()` on the final expression to force the engine to merge like terms and reduce dimensions.

## 4. CONSTANT vs SYMBOL RULE
Keep letter-named constants ($k$, $k_e$, $\epsilon_0$, $\mu_0$, $G$) as live SymPy symbols. Do not substitute numerical values unless the question explicitly asks for a numerical output.
- **Bad:** `ans = ["1.8e10 * h * q / (a**2 + h**2)**1.5"]`
- **Good:**
```python
import sympy as sp
k, q, h, a = sp.symbols('k q h a', positive=True)
expr = (2 * k * q * h) / (a**2 + h**2)**(1.5)
ans = [str(sp.simplify(expr))]
```