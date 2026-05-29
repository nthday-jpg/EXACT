import os
import sys
from pathlib import Path
import z3

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.logic.reasoning.verifier import verify_with_z3

def main():
    premises = [
        "ForAll(x, (WellTested(x) -> Optimized(x)))",
        "ForAll(x, (NOT FollowsPEP8(x)) -> NOT WellTested(x))",
        "ForAll(x, EasyToMaintain(x))",
        "ForAll(x, WellTested(x))",
        "ForAll(x, (FollowsPEP8(x)) -> EasyToMaintain(x))",
        "ForAll(x, (WellTested(x)) -> FollowsPEP8(x))",
        "ForAll(x, (WellStructured(x)) -> Optimized(x))",
        "ForAll(x, (EasyToMaintain(x)) -> WellTested(x))",
        "ForAll(x, (Optimized(x)) -> CleanReadable(x))",
        "ForAll(x, WellStructured(x))",
        "ForAll(y, CleanReadable(y))"
    ]

    opt_a = "ForAll(x, (NOT Optimized(x) -> NOT WellTested(x)))"
    opt_c = "ForAll(x, (WellTested(x) -> CleanReadable(x)))"

    print("Checking Option A (Entailment):")
    res_a = verify_with_z3(premises, opt_a, negate_conclusion=True)
    print(f"Result A: {res_a['result']}")
    print(f"Unsat Core A: {res_a.get('unsat_core')}")

    print("\nChecking Option C (Entailment):")
    res_c = verify_with_z3(premises, opt_c, negate_conclusion=True)
    print(f"Result C: {res_c['result']}")
    print(f"Unsat Core C: {res_c.get('unsat_core')}")

if __name__ == "__main__":
    main()
