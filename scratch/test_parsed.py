import z3
from src.logic.reasoning.parser import parse_formulas

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
    
    symbols, exprs = parse_formulas(premises)
    
    print("Numeric symbols:", symbols.numeric_symbols)
    print("Constants:")
    for name, const in symbols.consts.items():
        print(f"  {name}: {const} (Sort: {const.sort()})")
        
    print("\nFunctions:")
    for key, func in symbols.funcs.items():
        print(f"  {key}: {func} (Sort: {func.range()})")
        
    print("\nPredicates:")
    for key, pred in symbols.preds.items():
        print(f"  {key}: {pred}")
        
    print("\nParsed Formulas:")
    for idx, (p, expr) in enumerate(zip(premises, exprs), 1):
        print(f"  p_{idx}: {p}")
        print(f"    Z3: {expr}")
        print(f"    Z3 Python representation: {repr(expr)}")

if __name__ == "__main__":
    main()
