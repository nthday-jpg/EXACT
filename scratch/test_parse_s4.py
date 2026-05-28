from src.logic.reasoning.parser import parse_formulas
from src.utils.normalization import normalize_logic_fol_entry

def main():
    formulas = [
        "ForAll(x, (CompletedTraining(x) -> CanTeachUndergrad(x)))",
        "ForAll(x, ((CanTeachUndergrad(x) AND HoldsPhD(x)) -> CanSuperviseGraduate(x)))",
        "ForAll(x, ((CanSuperviseGraduate(x) AND >= 3Publications(x)) -> CanServeCommittee(x)))",
        "ForAll(x, ((CanServeCommittee(x) AND PositiveEvaluation(x)) -> CanProposeCourses(x)))",
        "CompletedTraining(john)",
        "HoldsPhD(john)",
        "ForAll(x, (Publications(x) >= 3))",
        "PositiveEvaluation(john)",
        "NOT (CanProposeCourses(john))"
    ]
    
    normalized_formulas = [normalize_logic_fol_entry(f) for f in formulas]
    print("Normalized formulas:")
    for f in normalized_formulas:
        print(f"  - {f}")
        
    try:
        symbols, exprs = parse_formulas(normalized_formulas)
        print("\nSuccess! Parsed all formulas correctly in Z3.")
    except Exception as e:
        print("\nFailed:", str(e))

if __name__ == "__main__":
    main()
