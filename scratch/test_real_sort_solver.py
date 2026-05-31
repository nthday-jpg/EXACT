import z3
from z3 import Solver, unsat, sat, DeclareSort, RealSort, Const, Function, BoolSort, ForAll, And, Or, Not

def main():
    # Let's define the sorts manually using RealSort
    U = DeclareSort("U")
    John = Const("John", U)
    
    CompletedCourses = Function("CompletedCourses", U, BoolSort())
    EligibleForGraduation = Function("EligibleForGraduation", U, BoolSort())
    GPA = Function("GPA", U, RealSort())
    GraduatesWithHonors = Function("GraduatesWithHonors", U, BoolSort())
    Thesis = Function("Thesis", U, BoolSort())
    AcademicDistinction = Function("AcademicDistinction", U, BoolSort())
    QualifiesForFellowship = Function("QualifiesForFellowship", U, BoolSort())
    NeedsRecommendation = Function("NeedsRecommendation", U, BoolSort())
    
    x = Const("x", U)
    
    premises = [
        ForAll([x], Or(Not(CompletedCourses(x)), EligibleForGraduation(x))),
        ForAll([x], Or(Not(And(EligibleForGraduation(x), GPA(x) > 3.5)), GraduatesWithHonors(x))),
        ForAll([x], Or(Not(And(GraduatesWithHonors(x), Thesis(x))), AcademicDistinction(x))),
        ForAll([x], Or(Not(AcademicDistinction(x)), QualifiesForFellowship(x))),
        CompletedCourses(John),
        GPA(John) == 3.8,
        Thesis(John)
    ]
    
    options = {
        "A": QualifiesForFellowship(John),
        "B": NeedsRecommendation(John),
    }
    
    for opt_char, opt_expr in options.items():
        solver = Solver()
        for p in premises:
            solver.add(p)
        solver.add(Not(opt_expr))
        
        res = solver.check()
        print(f"Checking option {opt_char}: Result: {res}")
        if res == unsat:
            print("  Entailed!")
        else:
            print("  Not Entailed!")

if __name__ == "__main__":
    main()
