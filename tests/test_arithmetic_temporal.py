import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

# Prevent shadowing the global 'z3' package
for path in list(sys.path):
    if path and Path(path).resolve() == Path(__file__).resolve().parent:
        sys.path.remove(path)

from src.logic.reasoning.verifier import parse_formulas, verify_with_z3, extract_proof_structure
from z3 import Solver, sat, unsat, Not, DeclareSort

def test_arithmetic():
    print("Running numeric pre-scan and arithmetic parsing tests...")
    # Test case: Sophia's score comparison (numeric)
    premises = [
        "active(sophia)",
        "score(sophia) = 8",
        "ForAll(x, (active(x) AND score(x) >= 8) -> eligible_scholarship(x))"
    ]
    conclusion = "eligible_scholarship(sophia)"
    
    # Verify that Z3 can prove the entailment
    symbols, exprs = parse_formulas(premises + [f"NOT ({conclusion})"])
    solver = Solver()
    solver.add(*exprs)
    res = solver.check()
    assert res == unsat, f"Expected unsat (entailed) but got {res}"
    print("[OK] Numeric pre-scanning and inequality checking passed successfully!")

def test_temporal():
    print("Running temporal and duration parsing tests...")
    # Test case: Chronological arithmetic
    # Time800AM = 8 * 60 = 480
    # Time500PM = 17 * 60 = 1020
    # Duration4Hours = 4 * 60 = 240
    # 1020 - 480 = 540 >= 240 -> True
    premises = [
        "TimeArrival(john) = Time800AM",
        "TimeDeparture(john) = Time500PM",
        "ForAll(x, (TimeDeparture(x) - TimeArrival(x) >= Duration4Hours) -> long_shift(x))"
    ]
    conclusion = "long_shift(john)"
    
    symbols, exprs = parse_formulas(premises + [f"NOT ({conclusion})"])
    solver = Solver()
    solver.add(*exprs)
    res = solver.check()
    assert res == unsat, f"Expected unsat (entailed) but got {res}"
    print("[OK] Temporal logic (Time & Duration) arithmetic passed successfully!")

def test_proof_extraction():
    print("Running proof structure extraction tests...")
    premises = [
        "Human(Socrates)",
        "ForAll(x, (Human(x) -> Mortal(x)))"
    ]
    conclusion = "Mortal(Socrates)"
    
    # We must enable proof generation
    import z3
    z3.set_param('proof', True)
    
    symbols, exprs = parse_formulas(premises + [f"NOT ({conclusion})"])
    solver = Solver()
    solver.add(*exprs)
    res = solver.check()
    assert res == unsat
    
    proof = solver.proof()
    structure = extract_proof_structure(proof)
    print("DEBUG: structure =", repr(structure))
    assert "Premise used" in structure or "Deduction" in structure
    print("[OK] Proof structure extraction passed successfully!")
    print("\nProof Skeleton generated:")
    print(structure)

if __name__ == "__main__":
    test_arithmetic()
    test_temporal()
    test_proof_extraction()
    print("\nAll arithmetic, temporal, and proof neurosymbolic tests passed successfully!")
