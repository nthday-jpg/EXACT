import z3
from z3 import Solver, unsat, sat
from src.logic.reasoning.verifier import parse_formulas

def check(premises, conclusion):
    all_formulas = premises + [f"NOT ({conclusion})"]
    symbols, exprs = parse_formulas(all_formulas)
    
    premise_exprs = exprs[:-1]
    negated_conclusion_expr = exprs[-1]
    
    solver = Solver()
    for idx, expr in enumerate(premise_exprs, 1):
        solver.assert_and_track(expr, z3.Bool(f"p_{idx}"))
    solver.assert_and_track(negated_conclusion_expr, z3.Bool("neg_conclusion"))
    
    res = solver.check()
    print(f"Checking conclusion: {conclusion} -> Result: {res}")
    if res == unsat:
        print(f"  Unsat core: {solver.unsat_core()}")

def main():
    premises = [
      "ForAll(x, (CompletedCourses(x) -> EligibleForGraduation(x)))",
      "ForAll(x, ((EligibleForGraduation(x) AND GPA(x) > 3.5) -> GraduatesWithHonors(x)))",
      "ForAll(x, ((GraduatesWithHonors(x) AND Thesis(x)) -> AcademicDistinction(x)))",
      "ForAll(x, (AcademicDistinction(x) -> QualifiesForFellowship(x)))",
      "CompletedCourses(John)",
      "GPA(John) = 3.8",
      "Thesis(John)"
    ]
    
    options = {
        "A": "QualifiesForFellowship(John)",
        "B": "NeedsRecommendation(John)",
        "C": "MustCompleteInternship(John)",
        "D": "NOT GraduatesWithHonors(John)"
    }
    
    for opt_char, opt_fol in options.items():
        check(premises, opt_fol)

if __name__ == "__main__":
    main()
