import sys
from pathlib import Path
import re

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
from src.logic.reasoning.parser import parse_formulas

premises = [
  "ForAll(x, (VehicleInspection(x) AND AppropriateLicense(x) -> TransportStandardGoods(x)))",
  "ForAll(x, (TransportStandardGoods(x) AND HazmatTraining(x) AND SafetyEndorsement(x) -> TransportHazardousMaterials(x)))",
  "ForAll(x, (TransportHazardousMaterials(x) AND InterstatePermit(x) -> CrossStateLinesWithHazardousCargo(x)))",
  "VehicleInspection(john)",
  "AppropriateLicense(john)",
  "HazmatTraining(john)",
  "NOT SafetyEndorsement(john)",
  "InterstatePermit(john)"
]

# We need to simulate the option translations.
option_formulas = {
    "A": "TransportHazardousMaterials(john) AND NOT CrossStateLinesWithHazardousCargo(john)",
    "B": "CrossStateLinesWithHazardousCargo(john)",
    "C": "NOT TransportHazardousMaterials(john)",
    "D": "NOT TransportStandardGoods(john) AND NOT TransportHazardousMaterials(john)"
}

symbols, premises_exprs = parse_formulas(premises)

for opt, f_str in option_formulas.items():
    print(f"\n--- Verifying Option {opt}: {f_str} ---")
    try:
        opt_sym, opt_exprs = parse_formulas([f_str])
        opt_expr = opt_exprs[0]
        
        # Verify if option is proven
        # Option is proven if premises AND NOT option is unsat
        solver = z3.Solver()
        for p in premises_exprs:
            solver.add(p)
        solver.add(z3.Not(opt_expr))
        res = solver.check()
        print(f"  Proven (unsat): {res == z3.unsat}")
        
        # Verify if negation is proven (i.e. Option is False)
        # Option is False if premises AND option is unsat
        solver2 = z3.Solver()
        for p in premises_exprs:
            solver2.add(p)
        solver2.add(opt_expr)
        res2 = solver2.check()
        print(f"  Disproven (unsat): {res2 == z3.unsat}")
        
    except Exception as e:
        print("Error:", e)
