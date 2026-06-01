### Common Failure Patterns

* **Vector Direction & Sign Errors:** Misinterpreting the physical direction of vector fields or forces (e.g., treating opposing charges as canceling forces at a midpoint instead of reinforcing).
* **Incorrect Physical Assumptions:** Assuming conservation of energy in dissipative processes, such as charge sharing between capacitors.
* **Formula Implementation Mistakes:** Omitting exponents or terms in standard equations (e.g., using $r$ instead of $r^2$ in Coulomb's Law).
* **Unit and Scale Mismatches:** Failing to convert input units (e.g., $\text{cm}^2$ to $\text{m}^2$) or output prefixes (e.g., $\text{J}$ to $\mu\text{J}$).
* **Sympy Execution Failures:** Attempting to convert symbolic expressions containing unresolved variables to floats, or passing unparseable mathematical strings to `sympy.Float`.
* **String Matching Discrepancies:** Providing incomplete conceptual descriptions or returning lists instead of the exact expected string format.

---

### Concise Heuristics

* **Enforce Explicit Vector Analysis:** Always draw or define coordinate axes and use absolute magnitudes with explicit directional unit vectors for force and field calculations.
* **Validate Unit Conversions Early:** Convert all input parameters to SI base units before executing calculations, and explicitly scale the final output to match the requested target unit prefix.
* **Verify Physical Constraints:** Double-check thermodynamic and electromagnetic conservation laws (e.g., energy is not conserved when ideal capacitors share charge).
* **Sanitize Sympy Inputs:** Ensure all variables are substituted with numerical values before calling `.evalf()`, and avoid passing algebraic expressions inside `sympy.Float()`.
* **Standardize Text Outputs:** For conceptual questions, match the exact phrasing of standard textbook definitions and avoid symbolic shorthand.

### Common Failure Patterns

*   **Vector Component Neglect:** Failing to resolve electric fields or forces into vector components (e.g., adding magnitudes directly instead of computing 2D/3D vector sums).
*   **Qualitative vs. Quantitative Mismatches:** Outputting numerical values, formulas, or ratios when the question asks for a qualitative or binary answer (e.g., "Yes/No", "Doubled", or a list of physical properties).
*   **Unit Prefix Discrepancies:** Calculating answers in standard SI base units (e.g., $\text{F}$, $\text{m}$) instead of the requested prefixed units (e.g., $\mu\text{F}$, $\text{cm}$).
*   **SymPy Solver Crashes:** Using complex symbolic constraints (like `sp.Abs` or uninstantiated symbols) in `sympy.solve` which prevents evaluation to a real float.
*   **Basic Formula Typos:** Missing exponents in fundamental physics equations (e.g., using $E = kq/r$ instead of $E = kq/r^2$).

---

### Concise Heuristics for System Prompts

*   **Enforce Question-Type Matching:** If a question asks "does [X] occur", "how does [X] change", or "what quantities", the output must be a qualitative string matching the requested format, not a raw number or formula.
*   **Explicit Unit Conversion:** Always check the target unit in the question (e.g., $\text{cm}$, $\mu\text{F}$) and explicitly convert the final Python numerical output to match that unit before rounding.
*   **Vector Geometry Verification:** For any multi-charge configuration, force the model to define coordinate vectors and perform vector addition ($\sum F_x, \sum F_y$) rather than scalar arithmetic.
*   **Robust Numerical Solving:** Avoid symbolic solvers for simple algebraic relations; rearrange equations algebraically in the prompt reasoning first, then use direct numerical evaluation in Python.

```json
{
  "results": [
    {
      "question": "Given XL = 28 Ω, XC = 112 Ω, and the total supply voltage U = 130 V. If the frequency is doubled, what is the RMS voltage across the resistor?",
      "why_fail": "The model failed to recognize that doubling the frequency results in a resonance condition (XL_new = XC_new), which means the entire supply voltage drops across the resistor. Instead, it hallucinated a resistor value of 30 Ω and calculated an incorrect voltage.",
      "fix_suggestion": "Instruct the model to analyze resonance conditions in AC circuits (i.e., when inductive reactance equals capacitive reactance) before assuming or hallucinating missing parameters like resistance."
    },
    {
      "question": "Two point charges, q1 = 0.5 nC and q2 = –0.5 nC, are placed at points A and B, separated by 6 cm in air. What is the magnitude of the electric field intensity at point M, which lies on the perpendicular bisector of AB, at a distance ℓ = 4 cm from the midpoint of AB?",
      "why_fail": "The model set up incorrect coordinates for the charges and the target point M, resulting in wrong distance vectors and incorrect electric field calculations.",
      "fix_suggestion": "When solving multi-charge electrostatic problems, explicitly set up a Cartesian coordinate system where the positions of all charges and the target point are correctly mapped relative to a chosen origin (e.g., the midpoint of the line segment connecting the charges)."
    },
    {
      "question": "In a vacuum, consider two electric charges q1 = -q2 = 10^{-7} C placed at points A and B, separated by 8 cm. Determine the resultant force acting on electric charge q0 = 10^{-7} C when q0 is placed at H, which is the midpoint of AB.",
      "why_fail": "The model used a highly precise value for Coulomb's constant (ke = 8.988e9) instead of the standard textbook approximation (9.0e9), leading to a slight numerical mismatch with the ground truth.",
      "fix_suggestion": "For electrostatic problems, use Coulomb's constant $k_e = 9.0 \\times 10^9\\ \\text{N}\\cdot\\text{m}^2/\\text{C}^2$ as the default standard textbook value unless specified otherwise."
    },
    {
      "question": "An RLC circuit has R=20 Ω, L=0.159 H, and C=10 μF. Is the circuit in resonance at f=126 Hz?",
      "why_fail": "The model used a strict float equality check (== 0) to determine resonance, which failed due to rounding in the textbook values. Additionally, it output a numeric 0 instead of a qualitative 'Yes' or 'No' string.",
      "fix_suggestion": "For qualitative or Yes/No questions, the final answer must be a string (e.g., 'Yes' or 'No'). When checking physical conditions like resonance in numerical calculations, use a tolerance threshold (e.g., within 1% relative difference) rather than strict equality."
    },
    {
      "question": "A 0.6 m long solenoid has 1200 turns and a cross-sectional area of 5 cm². Calculate the inductance of the solenoid.",
      "why_fail": "The model passed a mathematical expression containing 'pi' inside `sympy.Float()`, which caused a SymPy execution error. It also performed an incorrect unit conversion for the area (converting 5 cm² to 0.05 m² instead of 5e-4 m²).",
      "fix_suggestion": "Never pass mathematical expressions or constants like 'pi' inside `sympy.Float()`. Instead, define them using SymPy symbolic constants (e.g., `4 * sp.pi * 1e-7`). Always double-check unit conversions (e.g., cm² to m² is $10^{-4}$)."
    },
    {
      "question": "Three identical charges q = +6 * 10^{-8} C are placed at the three vertices of an isosceles right triangle with legs of 15 cm. Calculate the net force acting on the charge at the right-angle vertex.",
      "why_fail": "The model calculated the net force acting on one of the acute-angle vertices instead of the right-angle vertex as requested by the question.",
      "fix_suggestion": "Carefully identify which specific point or vertex is the target of the question (e.g., the right-angle vertex vs. an acute-angle vertex) and compute the forces/fields acting on that specific position."
    },
    {
      "question": "Two point charges q1 and q2 are placed at A and B, with AB = 2 cm. Given that q1 + q2 = 7 x 10^{-8} C. At point M, which is 6 cm from q1 and 8 cm from q2, the net electric field strength is E = 0. Find q2.",
      "why_fail": "The model restricted the charge symbols to be positive (`positive=True`), which prevented SymPy from finding a solution because the charges must have opposite signs for the electric field to cancel at point M.",
      "fix_suggestion": "Do not prematurely restrict symbol assumptions (like `positive=True`) in SymPy unless explicitly stated in the problem, as charges or other physical quantities can be negative."
    },
    {
      "question": "Two charges, q1 = +1 * 10^{-7} C and q2 = -1 * 10^{-7} C, are placed at points A and B, respectively, 12 cm apart. A test charge q = 10^{-6} C is placed at point M, which lies on the perpendicular bisector of the line segment AB, 5 cm away from AB (or from the midpoint of AB). Calculate the net electric force acting on the test charge q.",
      "why_fail": "The model assumed the force vectors were purely horizontal and ignored the vertical components/angles of the force vectors, leading to an incorrect magnitude calculation.",
      "fix_suggestion": "When calculating vector quantities (like force or electric field) from multiple sources, always project the vectors onto the coordinate axes using proper trigonometric relations or unit vectors, rather than assuming they lie entirely along one axis."
    },
    {
      "question": "An air-filled parallel plate capacitor has a plate area of 42.3 cm² and a plate separation of 1.02 mm. Calculate the capacitance of the capacitor. Give your answer rounded to two decimal places.",
      "why_fail": "The model made a unit conversion error, converting 42.3 cm² to 0.423 m² instead of 4.23e-3 m².",
      "fix_suggestion": "Ensure unit conversions for area (e.g., cm² to m²) are done correctly by multiplying by $10^{-4}$."
    },
    {
      "question": "Two point charges q1 = 2 * 10^{-2} μC and q2 = –2 * 10^{-2} μC are placed at two points A and B, separated by a distance a = 30 cm, in air. What is the magnitude of the electric field strength at point M, which is equidistant from A and B by a distance a = 30 cm?",
      "why_fail": "The model defined inconsistent coordinates that did not represent an equilateral triangle, resulting in incorrect distance vectors and a wrong electric field magnitude.",
      "fix_suggestion": "For geometric configurations like equilateral triangles, use correct trigonometric coordinates (e.g., vertices at $(0,0)$, $(a, 0)$, and $(a/2, a\\sqrt{3}/2)$) to ensure all distances match the problem description."
    }
  ]
}
```

{
  "results": [
    {
      "question": "A capacitor has a voltage of 10 V and a capacitance of 8 \u03bcF. If it's replaced by another capacitor with a capacitance of 4 \u03bcF, while maintaining the same voltage, what is the reduction in energy?",
      "why_fail": "The model calculated the absolute reduction in energy (in Joules) instead of the percentage reduction (50%), which was expected by the ground truth.",
      "fix_suggestion": "When a question asks for 'reduction' or 'increase' without specifying a unit, and the context suggests a relative change, calculate and output the percentage or fractional change rather than the absolute difference."
    },
    {
      "question": "Circuit AB satisfies LC\u03c9\u00b2 = 1. Voltages uAM and uMB are 90\u00b0 out of phase. Given R1 = 80 \u03a9 and R2 = 90 \u03a9. Calculate the power factor of the entire circuit.",
      "why_fail": "The SymPy code failed to convert the final expression to a float because the symbol 'XC' was not fully substituted/solved in the final power factor expression.",
      "fix_suggestion": "Ensure that all symbolic variables in SymPy equations are fully solved and substituted with their numerical values before attempting to evaluate the expression to a float."
    },
    {
      "question": "Three charges, q1 = q2 = q3 = -4 * 10^{-6} C, are placed at the three vertices of an equilateral triangle with sides of 15 cm. Calculate the net electric force acting on q3.",
      "why_fail": "The model defined the coordinates of the vertices incorrectly, leading to an incorrect angle (120 degrees instead of 60 degrees) between the force vectors.",
      "fix_suggestion": "For geometry-based physics problems, explicitly define the 2D/3D coordinates of all points/charges first, and then programmatically compute the displacement vectors to ensure correct angles and directions."
    },
    {
      "question": "An ideal LC circuit oscillates with constant total energy. At t = T/4, WL = 0. Calculate WC.",
      "why_fail": "The question is conceptual and expects a symbolic/descriptive answer, but the model assumed a dummy numerical value of 1 J to satisfy a float output format.",
      "fix_suggestion": "If a question is conceptual or asks for a qualitative state (e.g., 'maximum', 'zero', or a formula), output the descriptive string or symbolic expression directly instead of forcing a dummy numerical value."
    },
    {
      "question": "Two charges q1 = -2.4 * 10^{-6} C and q2 = 1.2 * 10^{-6} C are placed at two points separated by 9.2 cm. A point M is located 2.0 cm from q1 and 7.2 cm from q2. Calculate the total electric field intensity at M. Give your answer rounded three decimal places.",
      "why_fail": "The model used the precise value of Coulomb's constant (8.988e9) instead of the standard rounded textbook value (9.0e9), leading to a slight numerical mismatch.",
      "fix_suggestion": "Use 9.0e9 N*m^2/C^2 as the default value for Coulomb's constant (ke) in electrostatic problems unless the prompt specifies otherwise, as standard textbook problems often use this rounded value."
    },
    {
      "question": "Two test charges q1 and q2 (q1 = 4q2) are placed at points A and B respectively in an electric field. The force acting on q1 is F1, and the force acting on q2 is F2 (with F1 = 3F2). Let E1 and E2 be the electric field strengths at A and B respectively. What is the relationship between E1 and E2?",
      "why_fail": "The model output the numerical ratio (0.75) instead of the symbolic equation representing the relationship (E1 = (3/4)E2).",
      "fix_suggestion": "When asked for a 'relationship' between two variables, express the final answer as an equation (e.g., 'E1 = (3/4)E2') rather than just a numerical ratio."
    },
    {
      "question": "A parallel-plate air capacitor has a plate area of 31.0 cm\u00b2 and the distance between the two plates is 0.84 mm. Calculate the capacitance of the capacitor.",
      "why_fail": "The model incorrectly converted the plate area from cm^2 to m^2, using 0.31 m^2 instead of 31.0e-4 m^2.",
      "fix_suggestion": "Double-check unit conversions for area and volume (e.g., 1 cm^2 = 1e-4 m^2, not 1e-2 m^2) to prevent scaling errors in physical formulas."
    },
    {
      "question": "Consider an RLC series circuit with fixed components. When the angular frequency is \u03c90, the inductive reactance XL = 50 \u03a9 and the capacitive reactance XC = 200 \u03a9. By what factor must the angular frequency be adjusted (relative to \u03c90) for the circuit to resonate?",
      "why_fail": "The model incorrectly assumed the initial state was already at resonance, setting the initial frequency equal to the resonance frequency.",
      "fix_suggestion": "Do not assume a circuit is initially at resonance. Use the given reactances at the initial frequency to establish the relationship between the initial frequency and the resonance frequency."
    },
    {
      "question": "Two electric charges q1 = 5 * 10^{-9} C and q2 = \u20135 * 10^{-9} C are placed at two points separated by 10 cm in a vacuum. Calculate the magnitude of the electric field strength at a point located on the straight line passing through the two charges, and which is 5 cm from q1 and 15 cm from q2.",
      "why_fail": "The model correctly subtracted the opposing electric field vectors, but the ground truth incorrectly added their magnitudes despite the charges having opposite signs and the point being outside the segment.",
      "fix_suggestion": "When calculating electric fields from multiple charges along a line, carefully determine the direction of each field vector based on the sign of the charge and the position of the point relative to the charges."
    },
    {
      "question": "Given two charges q1 = 4 * 10^{-10} C and q2 = -4 * 10^{-10} C, placed at points A and B respectively, in air. The distance between A and B is AB = a = 2 cm. Determine the net electric field vector at point N, such that A, B, and N form an equilateral triangle.",
      "why_fail": "The model output both the magnitude and direction (as a list) because the question asked for the 'vector', whereas the ground truth only expected the magnitude.",
      "fix_suggestion": "When a question asks for a 'vector' quantity but does not explicitly request components or direction angles, default to outputting only the magnitude of the vector."
    }
  ]
}

{
  "results": [
    {
      "question": "Three identical charges 'q' are placed at the three vertices of an equilateral triangle with side length 'a'. Find the net electric force acting on a test charge placed at the center of the triangle?",
      "why_fail": "The generated Python code failed because it passed a non-numeric algebraic string ('sqrt(3)/2') to `sp.Float()`, which only accepts numeric strings.",
      "fix_suggestion": "Instruct the model to never pass algebraic expressions or non-numeric strings to `sp.Float()`. Instead, use SymPy's symbolic expressions (e.g., `sp.sqrt(3)/2`) or evaluate them numerically first."
    },
    {
      "question": "Three identical charges, q = +3 * 10^{-8} C, are placed at the three vertices of an isosceles right triangle with legs of 15 cm. Calculate the net force acting on the charge at the right-angle vertex. Give your answer rounded to three decimal places.",
      "why_fail": "The model used a slightly different value for Coulomb's constant (8.988e9 instead of 9e9), leading to a small discrepancy in the final rounded value.",
      "fix_suggestion": "Add a rule to the system prompt specifying standard physical constants to use (e.g., Coulomb's constant $k_e = 8.99 \\times 10^9$ or $9.0 \\times 10^9$ N m^2/C^2) to ensure consistency with standard textbook answers."
    },
    {
      "question": "Three electric charges q1 = q2 = q3 = +9 * 10^{-7} C are placed at the 3 vertices of an equilateral triangle with a side length of 12 cm. Calculate the net electric force acting on q3.",
      "why_fail": "The model incorrectly calculated the vector components of the forces, performing an incorrect projection and summing them incorrectly instead of using proper vector addition.",
      "fix_suggestion": "Instruct the model to use explicit coordinate geometry (e.g., defining vertices as SymPy Points) and vector math for multi-charge force/field problems to avoid manual projection errors."
    },
    {
      "question": "Three charges, q1 = q2 = q3 = +1 * 10^{-7} C, are placed at the three vertices of an equilateral triangle with a side length of 10 cm. Calculate the net electric force acting on q3.",
      "why_fail": "The model passed an angle in degrees (60) directly to `sp.cos` and `sp.sin` without converting it to radians, leading to incorrect trigonometric evaluations.",
      "fix_suggestion": "Explicitly instruct the model that SymPy trigonometric functions (`sp.sin`, `sp.cos`, etc.) expect arguments in radians, and any degree values must be converted using `sp.rad()` or multiplied by `sp.pi / 180`."
    },
    {
      "question": "What is the total resistance of two 10Ω and 30Ω branches connected in parallel?",
      "why_fail": "The model's answer was correct, but the evaluation failed because the ground truth contained a variable prefix ('Rtd = 7.5') while the model outputted only the numeric value.",
      "fix_suggestion": "Ensure the evaluation parser strips variable prefixes (like 'Rtd =') from the ground truth, or instruct the model to match potential variable assignment formats if detected in the context."
    },
    {
      "question": "L = 0.05 H, C = 40 µF, R = 20 Ω. What is the value of Q?",
      "why_fail": "The model's answer (1.768) was slightly more precise than the ground truth (1.77), leading to a mismatch due to strict string matching or rounding differences.",
      "fix_suggestion": "Instruct the model to round final answers to 3 significant figures or 2-3 decimal places by default, or implement a tolerance-based numeric comparison in the evaluation pipeline."
    },
    {
      "question": "A capacitor has an energy of 0.1 mJ and a voltage of 5 V. Calculate its capacitance.",
      "why_fail": "The model calculated the capacitance in Farads (F) instead of microfarads (μF) because the target unit was not explicitly specified in the question, but the ground truth expected μF.",
      "fix_suggestion": "Instruct the model to convert extremely small or large values to standard engineering units (e.g., μF for capacitance, mH/μH for inductance) when the question does not specify a unit but standard practice dictates it."
    },
    {
      "question": "Three identical charges, each with q = -6 * 10^{-8} C, are placed at the three vertices of an isosceles right triangle with legs of 20 cm. Calculate the net force acting on the charge at the right angle.",
      "why_fail": "The model outputted the answer in standard decimal notation (0.001144) while the ground truth used scientific notation (1.144 * 10^{-3}), causing a string mismatch.",
      "fix_suggestion": "Implement a numeric parser in the evaluation script to compare values mathematically rather than as raw strings, or instruct the model to format small numbers in scientific notation."
    },
    {
      "question": "Two charges, q1 = +2.6 * 10^{-6} C and q2 = -2.6 * 10^{-6} C, are placed at points A and B, separated by 8.1 cm. Point M lies on the perpendicular bisector of AB and is 4.9 cm from the line segment AB. Calculate the resultant electric field strength at M. Give your answer rounded three decimal places.",
      "why_fail": "The model performed a simple scalar addition of the electric field magnitudes instead of vector addition, neglecting the directional components of the electric fields.",
      "fix_suggestion": "Emphasize in the system prompt that electric fields and forces are vector quantities, and their resultant must always be calculated using vector addition (decomposing into components) rather than scalar addition."
    },
    {
      "question": "Given an inductor with L = 0.04 H, what capacitance C is needed to resonate at a frequency f = 250 Hz?",
      "why_fail": "The model calculated the capacitance in Farads (F) instead of microfarads (μF), leading to a unit mismatch with the ground truth.",
      "fix_suggestion": "Instruct the model to output capacitance in microfarads (μF) and inductance in millihenries (mH) by default if the calculated values are in those typical ranges, or check for implicit unit expectations."
    }
  ]
}

{
  "results": [
    {
      "question": "A series circuit has an inductive reactance XL = 5 Ω and a capacitive reactance XC = 180 Ω, with an applied RMS voltage of U = 100 V. If the frequency is increased by 6 times, what is the RMS voltage across R?",
      "why_fail": "The generated python code failed with a NameError because 'R' was not defined. The model failed to recognize that at the new frequency, the circuit reaches resonance (XL = XC = 30 Ω), meaning the total impedance equals R, and the voltage across R is simply the source voltage U, causing R to cancel out.",
      "fix_suggestion": "If a variable (like resistance R) is not numerically specified in the problem, define it as a symbolic variable in SymPy and simplify the final expression symbolically. If the expression simplifies to a constant independent of that variable, evaluate that constant."
    },
    {
      "question": "The true value of the object is 50.0 cm. The student measured 49.4 cm. Calculate the absolute error and the relative error.",
      "why_fail": "The model converted the inputs to meters and calculated the absolute error in meters and the relative error as a fraction, whereas the ground truth expected the original units (cm) and percentage (%) for the relative error.",
      "fix_suggestion": "Always perform calculations using the units explicitly requested or implied by the question's context (e.g., keep cm if inputs are in cm, and convert relative error to percentage if '%' is expected). Do not default to SI units if the question implies other units."
    },
    {
      "question": "A parallel-plate air capacitor has a plate area of 35.6 cm² and the distance between the plates is 0.91 mm. Calculate its capacitance. Give your answer rounded to two decimal places.",
      "why_fail": "The model performed an incorrect unit conversion for the area (converting 35.6 cm² to 0.356 m² instead of 0.00356 m²) and output the result in Farads (F) instead of picofarads (pF).",
      "fix_suggestion": "Ensure unit conversions are mathematically correct (especially area and volume conversions, e.g., 1 cm² = 10^-4 m²). Also, detect the standard prefix for the output unit (e.g., pF for small capacitances) or match the expected standard unit scale."
    },
    {
      "question": "Three identical charges q = 2.6 * 10^{-6} C are placed at the three vertices of an isosceles right triangle with side length 9.7 cm. Calculate the net electric field strength at the right-angle vertex.Give your answer rounded two decimal places.",
      "why_fail": "The model used N/C as the unit instead of V/m, and used ke = 8.988e9 which resulted in 3.51e6 instead of 3.52e6 (which uses ke = 9e9).",
      "fix_suggestion": "Use standard electrostatic constant ke = 8.98755e9 or 8.99e9 N·m²/C² (or 9e9 if standard high school physics rounding is implied). Ensure that equivalent units like N/C and V/m are mapped correctly to the expected ground truth unit."
    },
    {
      "question": "Three identical charges, q = 1.2 * 10^{-6} C, are placed at the three vertices of an isosceles right triangle with legs of length 5.2 cm. Calculate the net electric field at the right-angle vertex. Give your answer two decimal places.",
      "why_fail": "The model calculated the vector sum of the electric fields at the right-angle vertex due to the other two charges, resulting in sqrt(2)*ke*q/d^2. However, the ground truth expected 2*ke*q/d^2, which corresponds to either a scalar sum or the field at the midpoint of the hypotenuse.",
      "fix_suggestion": "For electric field problems on triangles where the question might contain a translation or conceptual error (e.g., asking for the field at a vertex where a charge is already present, or expecting a scalar sum), check if the expected answer corresponds to the field at the midpoint of the hypotenuse (2*ke*q/d^2) or a simple scalar sum of the fields."
    },
    {
      "question": "Three identical charges, q = +7 * 10^{-6} C, are placed at the three vertices of an isosceles right triangle with equal sides of 10 cm. Calculate the net force acting on the charge at the right-angle vertex.",
      "why_fail": "The model calculated the net force on an acute-angle vertex (C) instead of the right-angle vertex (A), due to a coordinate mapping error.",
      "fix_suggestion": "Carefully map the geometric description to coordinates. For an isosceles right triangle with equal sides a, place the right-angle vertex at the origin (0,0) and the other two vertices at (a,0) and (0,a) to ensure correct identification of the vertices."
    },
    {
      "question": "A solenoid has a cross-sectional area of 8 cm² and a magnetic field strength of 1.5 * 10^{-3} T. Calculate the magnetic energy density.",
      "why_fail": "The python code failed because it tried to parse '4*pi*1e-7' inside sympy.Float(), which only accepts simple float strings.",
      "fix_suggestion": "Do not pass expressions with mathematical constants (like pi) or operations (like *) into sympy.Float(). Instead, use sympy.pi and symbolic multiplication, e.g., 4 * sympy.pi * 1e-7."
    },
    {
      "question": "An RLC series circuit is connected to an AC power source with an RMS voltage U = 150 V. At resonance, the RMS voltages across the R-C combination and the C-L combination are equal, and both are 180 V. Calculate the RMS voltage across the capacitor C.",
      "why_fail": "The model assumed the voltage across the capacitor was simply equal to the voltage across the C-L combination (180 V), failing to apply the correct AC phasor relationships (U_RC = sqrt(U_R^2 + U_C^2)).",
      "fix_suggestion": "For AC circuits, always use phasor/vector relationships (e.g., U_RC = sqrt(U_R^2 + U_C^2), U_RL = sqrt(U_R^2 + U_L^2)) to relate voltages across combinations of components, rather than assuming direct equality."
    },
    {
      "question": "Given that the induced electromotive force is 0.3 V, and the current decreases uniformly from 2 A to 0 A in 0.05 s. Calculate the self-inductance.",
      "why_fail": "The model calculated a negative value for self-inductance because it strictly followed the formula EMF = -L * (dI/dt) where dI/dt was negative.",
      "fix_suggestion": "Physical quantities like inductance, capacitance, resistance, and distance must always be positive. Use absolute values when calculating these quantities from EMF or other signed relationships."
    },
    {
      "question": "Given an RLC series circuit with fixed components. When the angular frequency is ω0, the inductive reactance X_L = 22 Ω and the capacitive reactance X_C = 198 Ω. To what multiple of ω0 must the angular frequency be adjusted for the circuit to resonate?",
      "why_fail": "The model output the unit as 'multiple of ω0' instead of '-' (dimensionless), and did not format the answer to the expected float precision (3.0).",
      "fix_suggestion": "When asked for a 'multiple' or ratio, the unit should be dimensionless (represented as '-' or empty string ''), and the value should be formatted to the requested precision (or standard float representation like 3.0)."
    }
  ]
}

{
  "results": [
    {
      "question": "Two charges, q1 = 3.75 * 10^{-6} C and q2 = 3.14 * 10^{-6} C, are placed 6.62 cm apart. Calculate the electric field strength at a point on the perpendicular bisector, where the point is 3.31 cm from each of the two charges. Give your answer rounded to two decimal places.",
      "why_fail": "Physics logic error in the generated Python code: the model incorrectly assumed orthogonal vector addition (using Pythagoras) instead of recognizing that the point lies directly on the line segment between the charges (since 3.31 + 3.31 = 6.62), resulting in incorrect component summation.",
      "fix_suggestion": "Instruct the model to carefully verify the geometry of charge placements and point coordinates before performing vector addition, ensuring it projects field components correctly along the coordinate axes."
    },
    {
      "question": "What capacitor is needed for a 0.02 H inductor to resonate at 120 Hz?",
      "why_fail": "Unit mismatch: the model calculated the correct physical value in Farads (F) but failed to convert it to the expected microfarads (µF).",
      "fix_suggestion": "Add a rule to the system prompt requiring the model to check the standard metric prefixes (e.g., micro, milli, nano) commonly used for the target physical quantity and convert the final answer to match the expected unit scale."
    },
    {
      "question": "Two electric charges, q1 = +4.8 * 10^{-6} C and q2 = -4.8 * 10^{-6} C, are placed at two points A and B, separated by 5.2 cm. Consider point M as the midpoint of AB. Calculate the net electric field strength at M. Give your answer rounded two decimal places.",
      "why_fail": "Unit mismatch and rounding format issue: the model output the unit as 'N/C' instead of 'V/m' and did not format the final answer in standard scientific notation rounded to two decimal places.",
      "fix_suggestion": "Ensure the system prompt instructs the model to output electric field units as 'V/m' when requested, and strictly format scientific notation to match the requested rounding precision (e.g., '1.28 * 10^{8}')."
    },
    {
      "question": "Two point charges, q1 = 2.24 * 10^{-6} C and q2 = 1.24 * 10^{-6} C, are placed at the two ends of a straight line segment 8.25 cm long. Calculate the electric field strength at the midpoint of the line segment. Give your answer rounded to two decimal places.",
      "why_fail": "Precision mismatch and unit mismatch: the model did not round the final answer to two decimal places in scientific notation and used 'N/C' instead of 'V/m'.",
      "fix_suggestion": "Explicitly instruct the model to apply the requested rounding rules directly to the mantissa of the scientific notation before final output."
    },
    {
      "question": "Two electric charges, q1 = 4.2 * 10^{-6} C and q2 = 4.8 * 10^{-6} C, are separated by 6.0 cm. Point M lies on the line connecting the two charges (let's denote their positions as A and B respectively) but outside the segment AB. M is located 8.0 cm from A. Calculate the net electric field strength at M. Give your answer rounded two decimal places.",
      "why_fail": "Physics logic error in Python code: the model forgot to square the distance in the denominator of the electric field formula (using 'am' instead of 'am**2') and incorrectly subtracted the vectors.",
      "fix_suggestion": "Implement a strict code-review step in the prompt to double-check that standard physical formulas (like Coulomb's Law / Electric Field) are implemented with correct powers (e.g., r^2)."
    },
    {
      "question": "Two point charges, q1 = 0.5 nC and q2 = \u20130.5 nC, are placed at points A and B, 6 cm apart in air. What is the magnitude of the electric field strength at the midpoint of AB?",
      "why_fail": "Physics logic error: the model algebraically added the signed charges directly, causing the fields to cancel out to 0, instead of summing the absolute magnitudes of the fields which point in the same direction.",
      "fix_suggestion": "Instruct the model to determine the physical direction of electric field vectors based on charge signs before performing algebraic summation in Python."
    },
    {
      "question": "A circuit consists of a capacitor C = 75 \u03bcF in series with a resistor R = 10 \u03a9, at a frequency of 60 Hz. Calculate the capacitive reactance Z_C.",
      "why_fail": "Unit mismatch: the model output 'ohm' instead of the symbol 'Ω'.",
      "fix_suggestion": "Provide a mapping of common physical units to their standard symbols (e.g., 'Ω' for ohms) and instruct the model to use the symbol when appropriate."
    },
    {
      "question": "A parallel-plate capacitor with a capacitance of 100 pF is charged to 200 V. The power source is then disconnected, and the distance between its plates is doubled. Calculate the electrical energy stored in the capacitor after this change.",
      "why_fail": "Unit mismatch: the model output the answer in Joules ('J') instead of microjoules ('µJ').",
      "fix_suggestion": "Direct the model to identify the most reasonable prefix unit for small energy scales (like microjoules) and convert the final float accordingly."
    },
    {
      "question": "A parallel plate capacitor has a charge of 80 \u03bcC and a voltage of 400 V. Calculate the attractive force between the two plates if the area S = 50 cm\u00b2.",
      "why_fail": "Physics misinterpretation and unit mismatch: the model incorrectly converted the area from cm² to m² (using 0.5 m² instead of 0.005 m²) and output the force in 'N' instead of 'mN'.",
      "fix_suggestion": "Add a strict unit conversion verification step in the prompt, especially for area (cm² to m²) and force scales (N to mN)."
    },
    {
      "question": "The electric field strength produced by a point charge +Q at point A, a distance r away from it, has a magnitude of E (V/m). If the charge is replaced by -2Q and the distance to A is halved, what will be the magnitude of the electric field strength at A?",
      "why_fail": "Python code execution error: the model attempted to convert a symbolic expression containing undefined variables 'Q' and 'r' into a float, causing a runtime crash.",
      "fix_suggestion": "Instruct the model to solve symbolic ratio problems purely algebraically without attempting to evaluate the final expression as a float."
    }
  ]
}

{
  "results": [
    {
      "question": "Two electric charges, q1 = 4 * 10^–10 C and q2 = –4 * 10^–10 C, are placed at points A and B in air, with AB = 2 cm. Determine the electric field vector at point M, given that MA = 1 cm and MB = 3 cm.",
      "why_fail": "The model incorrectly set the coordinates of point M to be the same as point A (0,0), which resulted in a distance of 0 and a division-by-zero error (NaN). In reality, M, A, and B are collinear with M placed 1 cm to the left of A.",
      "fix_suggestion": "When setting up spatial coordinates for collinear points, verify that the assigned coordinates satisfy all given pairwise distances (e.g., if AB = 2, MA = 1, and MB = 3, then M, A, and B must be collinear in that order, such as M=-1, A=0, B=2)."
    },
    {
      "question": "Given that the magnetic flux per turn is 6 * 10^{-6} Wb and there are 400 turns. Calculate the total magnetic flux linkage.",
      "why_fail": "The model used the unit 'Wb-turn' instead of the standard SI unit 'Wb' for magnetic flux linkage, causing a unit mismatch with the ground truth.",
      "fix_suggestion": "Always express magnetic flux linkage in the standard SI unit of Webers (Wb) rather than composite units like 'Wb-turn'."
    },
    {
      "question": "Two charges, q1 = q2 = q (where q > 0, in Coulombs), are placed at points A and B, with the distance AB = 2a (meters). Point M is located on the perpendicular bisector of the line segment AB, at a distance h from AB. Determine the magnitude of the electric field vector at point M. Given k = 9 * 10^{9}.",
      "why_fail": "The generated Python code attempted to convert symbolic variables 'a' and 'h' into SymPy Float objects, which threw a 'string-float not recognized' error.",
      "fix_suggestion": "When a physics problem contains symbolic variables instead of numerical values, define them as SymPy symbols (e.g., sp.symbols('a h')) instead of trying to parse them as Float objects."
    },
    {
      "question": "Two electric charges, q1 = +2 μC and q2 = -2 μC, are placed 10 cm apart. A charge q3 = +1 μC is placed at the midpoint of the line segment connecting q1 and q2. Calculate the net force acting on q3.",
      "why_fail": "The model incorrectly assumed the forces from q1 and q2 on q3 cancel out to zero because of symmetry. Since q1 is positive and q2 is negative, the forces on a positive midpoint charge q3 both point in the same direction (away from q1 and towards q2) and should be added, not subtracted.",
      "fix_suggestion": "When calculating electrostatic forces or fields from multiple charges, treat them as vectors. Determine the direction of each vector component based on physical principles (like charges repel, opposite charges attract) before summing them, rather than performing a simple algebraic sum of signed scalar values."
    },
    {
      "question": "An inductor with L=0.25 H is used. What capacitance is required to achieve resonance at f=90 Hz?",
      "why_fail": "The model calculated the capacitance in Farads (F) but the ground truth expected the answer in microfarads (μF).",
      "fix_suggestion": "If the calculated value of a physical quantity is extremely small in standard SI units (e.g., capacitance in Farads), convert the final answer to common practical units (like μF, nF, or pF) or check if the context implies a specific prefix."
    },
    {
      "question": "A capacitor has an electric field energy of 0.48 J and a voltage of 240 V. What is its capacitance?",
      "why_fail": "The model calculated the capacitance in Farads (F) instead of microfarads (µF), leading to a unit and value mismatch.",
      "fix_suggestion": "Convert capacitance values to microfarads (µF) by default if the value is in the micro-range, as textbook problems typically express capacitance in µF."
    },
    {
      "question": "Two charges q1 = +7 * 10^{-8} C and q2 = -7 * 10^{-8} C are placed at two points A and B, 6 cm apart. A charge q3 = -7 * 10^{-8} C is placed at the midpoint of AB. Calculate the electric force acting on q3.",
      "why_fail": "The model incorrectly assumed the forces cancel out to zero. Because q1 is positive and q2 is negative, the forces on the negative midpoint charge q3 both point towards A (attracted to q1, repelled by q2) and must be summed vectorially.",
      "fix_suggestion": "For collinear charges, explicitly define a 1D coordinate system and compute the force vectors with correct signs based on position and charge, rather than adding scalar formulas that use signed charges directly without position vectors."
    },
    {
      "question": "A light bulb consumes 12W of power under a voltage of 6V. Calculate the current through the bulb.",
      "why_fail": "The model outputted the numerical value '2' but the ground truth expected the formatted string 'I = 2.0'.",
      "fix_suggestion": "If the question asks for a specific variable, ensure the output format can accommodate both the raw numerical value and the variable assignment format (e.g., 'I = 2.0') if required by the evaluation parser."
    },
    {
      "question": "Two point charges q1 = +3 * 10^{-6} C and q2 = -3 * 10^{-6} C are placed at two points A and B, separated by 10 cm. A charge q3 = -3 * 10^{-6} C is placed at the midpoint of AB. Calculate the electric force acting on q3.",
      "why_fail": "The model incorrectly assumed the forces cancel out to zero due to symmetric placement, ignoring that the opposite signs of q1 and q2 cause their forces on q3 to point in the same direction.",
      "fix_suggestion": "Always determine the direction of electrostatic forces using the physical rule that opposite charges attract and like charges repel before performing vector addition."
    },
    {
      "question": "Two charges, q1 = +2 * 10^{-8} C and q2 = -2 * 10^{-8} C, are placed at two points A and B, separated by 10 cm. A third charge, q3 = -2 * 10^{-8} C, is placed at the midpoint of AB. Calculate the electric force acting on q3.",
      "why_fail": "The model calculated a negative force value due to 1D vector direction, but the question asked for the force, which typically implies the magnitude (a positive value).",
      "fix_suggestion": "When asked to calculate a vector quantity like 'force' or 'electric field' without a specified coordinate axis, default to returning the absolute magnitude of the vector."
    }
  ]
}

{
  "results": [
    {
      "question": "Two point charges q1 = 4.78 * 10^{-6} C and q2 = 1.15 * 10^{-6} C are placed at two points separated by 8.06 cm. Calculate the electric field strength at a point on the perpendicular bisector, such that the point is 4.03 cm away from each charge. Give your answer rounded to two decimal places.",
      "why_fail": "The model incorrectly assumed the electric fields from the two charges were perpendicular, whereas the point actually lies on the line segment connecting the charges (midpoint), meaning the fields are collinear.",
      "fix_suggestion": "Before applying vector addition formulas, verify the geometric configuration of the points. If the sum of the distances from the point to each charge equals the distance between the charges, the point lies on the line segment connecting them, and the fields are collinear."
    },
    {
      "question": "In an RLC circuit with L = 0.015 H, what value of C is needed to achieve resonance at f = 500 Hz?\"",
      "why_fail": "Unit mismatch. The model calculated the capacitance in Farads (F) instead of microfarads (μF) as expected by the ground truth.",
      "fix_suggestion": "When solving for capacitance in AC/resonant circuits, convert the final answer to microfarads (μF) if the value is in the microfarad range, as this is the standard unit for such problems."
    },
    {
      "question": "Two electric charges, q1 = q2 = 5 * 10^{-16} C, are placed at vertices B and C of an equilateral triangle ABC with a side length of 8 cm, in air. What is the magnitude of the electric field strength at vertex A of the triangle?",
      "why_fail": "The model used ke = 8.988 * 10^9 for Coulomb's constant, whereas the ground truth used the standard rounded value of 9.0 * 10^9, leading to a small numerical discrepancy.",
      "fix_suggestion": "Use ke = 9.0 * 10^9 N*m^2/C^2 as the default value for Coulomb's constant in electrostatic calculations to align with standard textbook rounding."
    },
    {
      "question": "Given L = 0.005 H, what capacitance C is required to achieve resonance at 2000 Hz?",
      "why_fail": "Unit mismatch. The model output the capacitance in Farads (F) instead of microfarads (μF).",
      "fix_suggestion": "Always convert capacitance values in the microfarad range (10^-6 F) to microfarads (μF) for the final answer."
    },
    {
      "question": "A capacitor has a charge of 20 \u03bcC and a voltage of 5 V. Calculate the capacitance.",
      "why_fail": "The ground truth has a flawed unit ('nC' instead of 'μF' or 'F') and value ('0.100' instead of '4'), likely due to a mismatched question template or incorrect ground truth.",
      "fix_suggestion": "If a question asks for capacitance but the expected unit is a charge unit (like nC), check if the question text has swapped the terms 'charge' and 'capacitance' or if the formula Q = C * V was intended to solve for charge instead."
    },
    {
      "question": "In an LC circuit, at the moment the energy in the inductor (W_L) is \u2153 of the total energy, what percentage (%) is the energy in the capacitor (W_C) (round the result to the nearest whole number)?",
      "why_fail": "Python execution error. The model passed a fraction string '1/3' to sp.Float(), which is not supported by SymPy and caused a parsing crash.",
      "fix_suggestion": "Avoid passing fraction strings like '1/3' directly to sp.Float(). Use sp.Rational(1, 3) or perform float division like sp.Float('1') / 3."
    },
    {
      "question": "Two charges, q1 = 3.96 * 10^{-6} C and q2 = 4.13 * 10^{-6} C, are each located 5.58 cm from point M. The electric fields they produce at M are perpendicular to each other. Calculate the magnitude of the resultant electric field at M. Give your answer rounded two decimal places.",
      "why_fail": "The model used ke = 8.988 * 10^9 instead of the rounded 9.0 * 10^9, causing a slight numerical mismatch in the final rounded answer.",
      "fix_suggestion": "Use 9.0 * 10^9 N*m^2/C^2 for Coulomb's constant to ensure compatibility with textbook-derived ground truths."
    },
    {
      "question": "Two electric charges, q1 = +8 * 10^{-8} C and q2 = -8 * 10^{-8} C, are placed at points A and B, separated by 8 cm. A charge q3 = +8 * 10^{-8} C is placed at the midpoint of AB. Calculate the electric force acting on q3.",
      "why_fail": "The model performed a simple algebraic sum of signed forces (F1 + F2) without considering that the forces from a positive and a negative charge on a midpoint positive charge both point in the same direction and should add in magnitude.",
      "fix_suggestion": "When calculating net electrostatic force, determine the direction of each force vector individually (repulsive vs. attractive) and perform proper vector addition rather than summing signed scalar values directly."
    },
    {
      "question": "How is the oscillation period of an LC circuit calculated?",
      "why_fail": "The model output the formula in raw Python/SymPy syntax (2*pi*sqrt(C)*sqrt(L)) instead of the standard mathematical/LaTeX representation (T = 2\\pi\\sqrt(LC)).",
      "fix_suggestion": "When asked for a formula, format the output using standard mathematical notation or LaTeX (e.g., T = 2\\pi\\sqrt(LC)) rather than raw code expressions."
    },
    {
      "question": "Two electric charges q1 = -6 * 10^{-8} C and q2 = +5 * 10^{-8} C are placed at two points A and B, 8 cm apart, in air. A charge q3 = +2 * 10^{-8} C is placed at point C, knowing that the distance from C to A is 10 cm and from C to B is 8 cm. Calculate the net electric force acting on q3.",
      "why_fail": "The model used ke = 8.988 * 10^9 instead of 9.0 * 10^9, leading to a small rounding discrepancy in the final answer.",
      "fix_suggestion": "Use 9.0 * 10^9 N*m^2/C^2 for Coulomb's constant in electrostatic calculations to match standard textbook rounding."
    }
  ]
}

{
  "results": [
    {
      "question": "What capacitance C is needed for a 0.05 H inductor to resonate at 100 Hz?",
      "why_fail": "Unit mismatch. The model calculated the capacitance in Farads (F) instead of microfarads (µF) as expected by the ground truth.",
      "fix_suggestion": "Always check if the question or standard conventions imply a specific unit prefix (e.g., µF, mA, kV). Convert the final calculated value to the target unit prefix before outputting."
    },
    {
      "question": "A solenoid has a magnetic field B = 5 * 10^{-3} T and a cross-sectional area of 6 cm². Calculate the magnetic flux through the cross-section.",
      "why_fail": "Code implementation error. The model incorrectly converted the area from cm² to m² as 0.06 instead of 6e-4 (0.0006).",
      "fix_suggestion": "Use explicit conversion factors for area and volume units (e.g., 1 cm² = 1e-4 m²) in Python code to avoid manual decimal placement errors."
    },
    {
      "question": "A 24V source supplies 2 A of current to a circuit with two parallel lamps. Calculate the total power consumption of the circuit.",
      "why_fail": "Formatting mismatch. The model output the raw number '48', whereas the ground truth expected 'P = 48.0'.",
      "fix_suggestion": "When formatting the final answer, check if the question or dataset style expects a 'Variable = Value' format, and standardise the output format accordingly."
    },
    {
      "question": "The electric field energy in the capacitor gradually increases from zero to its maximum, while simultaneously the magnetic field energy decreases from its maximum to zero. What does this indicate about the oscillation process?",
      "why_fail": "Physics misinterpretation and code implementation error. The question is qualitative, but the model left the python code without assigning a string answer to the 'ans' variable.",
      "fix_suggestion": "For qualitative or conceptual questions, the Python code must assign the final text/string answer directly to the 'ans' variable (e.g., ans = ['Conservation of energy']) instead of leaving it empty."
    },
    {
      "question": "Consider a series RLC circuit with fixed components. When the angular frequency is ω0, the inductive reactance X_L = 90 Ω and the capacitive reactance X_C = 30 Ω. By what factor must the angular frequency be adjusted (relative to ω0) for the circuit to resonate?",
      "why_fail": "Python code execution error. The model defined 'omega' as a SymPy symbol but failed to resolve it algebraically, leading to a float conversion error.",
      "fix_suggestion": "Perform complete algebraic simplification to eliminate symbolic variables before calling float() on SymPy expressions. Ensure all symbols cancel out if a dimensionless ratio is requested."
    },
    {
      "question": "In an LC circuit, the electric field energy varies with time as: W_C = 0.5cos²(1000t). What is the magnetic field energy (J) at time t = π / 2000 s?",
      "why_fail": "Python code execution error. The model attempted to parse the string 'pi' using sp.Float('pi'), which is invalid in SymPy.",
      "fix_suggestion": "Never pass mathematical constants as strings to sp.Float(). Use SymPy's built-in constants directly (e.g., sp.pi, sp.E)."
    },
    {
      "question": "At two points A and B, separated by 10 cm in air, two electric charges q1 = q2 = 16 * 10^{-8} C are placed. Determine the electrostatic force acting on charge q3 = 2 * 10^{-6} C, which is placed at point C. Given that AC = BC = 8 cm.",
      "why_fail": "Physics misinterpretation and coordinate setup error. The model set the coordinates of the charges such that the distance r1 was 0, causing a division-by-zero error (NaN).",
      "fix_suggestion": "When solving 2D/3D vector physics problems, define a proper coordinate system (e.g., placing A at (-d/2, 0) and B at (d/2, 0)) and use the Pythagorean theorem to find non-zero coordinates for the third point."
    },
    {
      "question": "Two identical lamps are connected in parallel and consume a total of 18W. Calculate the power of each lamp.",
      "why_fail": "Formatting mismatch. The model output the raw number '9', whereas the ground truth expected 'P = 9.0'.",
      "fix_suggestion": "Ensure the system prompt has a post-processing step to normalize 'Variable = Value' formats to just the numerical value, or vice versa, to match the evaluation parser."
    },
    {
      "question": "Two electric charges, q1 = 4.25 * 10^{-6} C and q2 = 4.43 * 10^{-6} C, are both 5.51 cm away from point M. The electric fields they produce at M form an angle of 60° with each other. Calculate the magnitude of the resultant electric field at M. Give your answer rounded two decimal places.",
      "why_fail": "Physics logic error in Python code. The model calculated the electric field of a point charge using E = k*q/r instead of the correct formula E = k*q/r^2.",
      "fix_suggestion": "Double-check standard physics formulas in the code generation step. Specifically, verify that the electric field of a point charge uses the inverse-square law (r^2)."
    },
    {
      "question": "A capacitor has a charge Q = 50 μC and a capacitance C = 5 μF. If it's replaced with another capacitor having a capacitance of 10 μF, but the charge Q is kept constant, how does the voltage change?",
      "why_fail": "Physics misinterpretation. The question asks for a qualitative description of how the voltage changes, but the model output the raw initial and final numerical voltages.",
      "fix_suggestion": "Identify comparative or qualitative questions (e.g., containing 'how does ... change?') and output a descriptive text answer (e.g., 'halved' or 'decreased by half') rather than numerical values."
    }
  ]
}

{
  "results": [
    {
      "question": "An inductor L = 0.08 H resonates at f = 250 Hz. What is the capacitance C?",
      "why_fail": "The model calculated the capacitance in Farads (F) instead of converting it to microfarads (μF) as expected by the ground truth.",
      "fix_suggestion": "Always convert small capacitance values to standard sub-units (like μF, nF, pF) and check if the target unit is specified in the question or standard conventions."
    },
    {
      "question": "At the three vertices of a right isosceles triangle ABC, with AB = AC = a, three positive charges qA = qB = q and qC = 2q are placed in a vacuum. What is the expression for the electric field intensity at H, which is the foot of the altitude dropped from the right-angle vertex A to the hypotenuse BC?",
      "why_fail": "The model substituted a numerical value for Coulomb's constant (ke) instead of keeping it as a symbolic variable (k) in the algebraic expression.",
      "fix_suggestion": "When the question asks for an 'expression' involving symbolic variables, keep physical constants (like Coulomb's constant k) symbolic instead of substituting their numerical values."
    },
    {
      "question": "A parallel plate air capacitor has a plate area of 44.1 cm² and the distance between the two plates is 0.79 mm. Calculate the capacitance of the capacitor.",
      "why_fail": "The model incorrectly converted the area from cm² to m² (using 0.441 instead of 0.00441) and output the result in Farads instead of picofarads (pF).",
      "fix_suggestion": "Double-check unit conversions for area (1 cm² = 1e-4 m²) and volume. Express very small capacitance values in picofarads (pF) or microfarads (μF) unless Farads are explicitly requested."
    },
    {
      "question": "A series circuit has XL = 20 Ω, XC = 80 Ω, and U = 150 V. When the frequency is doubled, what is the RMS voltage across the resistor R?",
      "why_fail": "The generated Python code failed because it attempted to use the variable 'R' which was not defined in the problem, failing to recognize that at the new frequency the circuit is in resonance (XL = XC) and thus UR = U.",
      "fix_suggestion": "Perform a qualitative physical analysis before writing code. If a variable (like R) is not provided, check if the physical state (e.g., resonance) simplifies the equations such that the variable cancels out or is not needed."
    },
    {
      "question": "Two charges, q1 = 3.90 * 10^{-6} C and q2 = 2.21 * 10^{-6} C, are both located 5.47 cm away from point M. The electric fields they produce at M are perpendicular to each other. Calculate the magnitude of the resultant electric field at M. GIve your answer rounded two decimal places.",
      "why_fail": "The model output the answer in standard scientific notation (1.3466e7) instead of the requested format (13.48 * 10^{6}) and used N/C instead of V/m.",
      "fix_suggestion": "Format large numbers in the specific scientific notation style 'A * 10^{B}' and use V/m as the standard unit for electric field strength when requested."
    },
    {
      "question": "Two electric charges q1 = +7 * 10^{-6} C and q2 = -7 * 10^{-6} C are placed at points A and B, separated by 10 cm. A charge q3 = +7 * 10^{-6} C is placed at the midpoint of AB. Calculate the electric force acting on q3.",
      "why_fail": "The model assumed the forces from q1 and q2 on q3 cancel out due to symmetry, failing to realize that a positive charge is repelled by q1 and attracted by q2, meaning both force vectors point in the same direction and add up.",
      "fix_suggestion": "Always determine the direction of electrostatic force vectors based on the signs of the charges (like charges repel, opposite charges attract) before performing vector addition; do not assume symmetric placement always results in cancellation."
    },
    {
      "question": "Two charges q1 = -2 * 10^{-8} C and q2 = -5 * 10^{-8} C are placed at points A and B, 12 cm apart in the air. A third charge q3 = -5 * 10^{-8} C is placed at point C, given that the distance from C to A is 5 cm and the distance from C to B is 9 cm. Calculate the net electric force acting on q3.",
      "why_fail": "The model's numerical answer was correct but formatted as a decimal (0.003493) instead of the scientific notation (3.5 * 10^{-3}) expected by the ground truth.",
      "fix_suggestion": "For small decimal values (e.g., < 0.01), format the final output in scientific notation 'A * 10^{B}' to match standard physics answer keys."
    },
    {
      "question": "A capacitor C = 3 μF, is charged at 12 V, then its two plates are short-circuited. Calculate the charge and energy after short-circuiting.",
      "why_fail": "The model returned a list of separate answers and units instead of a single semicolon-separated string as expected by the ground truth format.",
      "fix_suggestion": "When a question asks for multiple quantities, format the final answer as a single string with values separated by semicolons (e.g., 'val1; val2') and units similarly joined (e.g., 'unit1; unit2')."
    },
    {
      "question": "Two electric charges, q1 = 2.38 * 10^{-6} C and q2 = 3.22 * 10^{-6} C, are placed at the two ends of a straight line segment 7.65 cm long. Calculate the electric field strength at the midpoint of that segment (on the line connecting them). Give your answer rounded to three decimal places.",
      "why_fail": "The model calculated a negative value due to vector subtraction direction, whereas 'strength' or 'magnitude' must always be positive. Additionally, the formatting did not match the expected 'A * 10^{B}' format.",
      "fix_suggestion": "Ensure that 'strength' or 'magnitude' of vector quantities is always returned as an absolute (positive) value, and format large numbers in 'A * 10^{B}' scientific notation."
    },
    {
      "question": "Three charges, q1 = q2 = q3 = 1.2 * 10^{-6} C, are placed at the three vertices of an equilateral triangle with a side length of 5.2 cm. Calculate the net electric field strength at the position of q3. Give your answer rounded two decimal places.",
      "why_fail": "The model used a slightly different value for Coulomb's constant (8.988e9 instead of 8.99e9 or 9e9) and did not format the output in the expected 'A * 10^{B}' scientific notation.",
      "fix_suggestion": "Use standard rounded physics constants (e.g., ke = 8.99e9 or 9.0e9) to avoid minor rounding discrepancies, and format large values in 'A * 10^{B}' notation."
    }
  ]
}

{
  "results": [
    {
      "question": "Two point charges q1 = -9 x 10^{-6} C and q2 = -4 x 10^{-6} C are placed at two points A and B, respectively, which are 20 cm apart in air. Calculate the magnitude of the resultant electric field strength at point C, given that AC = 30 cm and BC = 10 cm.",
      "why_fail": "The model used Coulomb's constant ke = 8.988e9 instead of the standard textbook approximation ke = 9e9 (or 9.0 x 10^9), leading to a small numerical discrepancy (4.494e6 vs 4.5e6) that failed to match the ground truth.",
      "fix_suggestion": "Instruct the model to use standard textbook approximations for physical constants (e.g., Coulomb's constant ke = 9.0e9 N*m^2/C^2, acceleration due to gravity g = 9.8 or 9.81 m/s^2 as appropriate, and pi = 3.14159) unless specified otherwise in the prompt."
    },
    {
      "question": "A solenoid has a length of 1.2 m and 2400 turns. The current is 1 A. Calculate the magnetic field strength.",
      "why_fail": "The generated Python code attempted to pass a symbolic expression string '4 * pi * 1e-7' to sympy.Float(), which threw a ValueError because sympy.Float only accepts numeric strings.",
      "fix_suggestion": "Instruct the model to never pass algebraic expressions or symbols (like 'pi' or arithmetic operators) inside a string to sympy.Float(). Instead, define constants using SymPy symbols directly (e.g., 4 * sp.pi * 1e-7) or evaluate them numerically beforehand."
    },
    {
      "question": "Two electric charges, q1 = +1 * 10^{-8} C and q2 = -1 * 10^{-8} C, are placed at points A and B, 10 cm apart. A test charge q = 10^{-8} C is placed at point M, which lies on the perpendicular bisector of AB and is 5 cm away from AB. Calculate the net electric force acting on q.",
      "why_fail": "The model used Coulomb's constant ke = 8.988e9, resulting in a force magnitude of 2.5422e-4 N, whereas using the standard textbook value of ke = 9e9 yields 2.5456e-4 N, which rounds to the correct answer of 2.55e-4 N.",
      "fix_suggestion": "Add a rule to the system prompt specifying that for electrostatic problems, Coulomb's constant (ke) should be set to exactly 9.0e9 (or 9e9) N*m^2/C^2 to ensure alignment with standard textbook rounding."
    }
  ]
}
