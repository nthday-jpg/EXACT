import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
from src.logic.reasoning.parser import parse_formulas

premises = [
    "ForAll(x, (Violence(x) -> (Good(x) -> Justified(x))))",
    "ForAll(x, (Justified(x) -> Lawful(x)))"
]

conclusion = "ForAll(x, (Violence(x) AND Good(x)) -> Lawful(x))"

all_formulas = premises + [f"NOT ({conclusion})"]
try:
    symbols, exprs = parse_formulas(all_formulas)
    solver = z3.Solver()
    for e in exprs[:-1]:
        solver.add(e)
    solver.add(exprs[-1])
    print("Proven (unsat):", solver.check() == z3.unsat)
except Exception as e:
    print("Error:", e)
