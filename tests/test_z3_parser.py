import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

# Remove the directory containing this script (tests/) from sys.path 
# to prevent shadowing the global 'z3' package
for path in list(sys.path):
    if path and Path(path).resolve() == Path(__file__).resolve().parent:
        sys.path.remove(path)

from src.logic.z3_verifier import parse_formulas, FolParser, Z3Symbols
from z3 import Solver, sat, unsat, Not, DeclareSort

def run_case(name: str, formulas: list[str], expect_sat: bool = True) -> None:
    symbols, exprs = parse_formulas(formulas)
    solver = Solver()
    solver.add(*exprs)
    result = solver.check()
    if expect_sat:
        assert result == sat, f"{name} expected sat but got {result}"
    else:
        assert result != sat, f"{name} expected non-sat but got {result}"

def run_parse_error_case(name: str, formulas: list[str]) -> None:
    try:
        parse_formulas(formulas)
    except ValueError:
        return
    raise AssertionError(f"{name} expected ValueError")

def check_entailment(premises: list[str], conclusion: str) -> bool:
    """Check if the premises logically entail the conclusion."""
    symbols, premise_exprs = parse_formulas(premises)
    parser = FolParser(symbols)
    conclusion_expr = parser.parse(conclusion)
    
    solver = Solver()
    solver.add(*premise_exprs)
    solver.add(Not(conclusion_expr))
    
    result = solver.check()
    return result == unsat

# Test Case 1: Consistency (satisfiability) of numeric comparisons
run_case(
    "numeric_comparison",
    formulas=[
        "active_status(sarah)", 
        "completed_courses(sarah) = 4", 
        "has_approval(sarah)",
        "ForAll(x, (active_status(x) AND completed_courses(x) >= 5) -> eligible_advanced(x))",
        "ForAll(x, eligible_advanced(x) -> requires_approval(x))",
    ],
)

# Test Case 2: Membership IN
run_case(
    "membership_in",
    formulas=[
        "alice IN group1",
        "ForAll(x, (x IN group1) -> member(x))",
    ],
)

# Test Case 3: Nested quantifiers
run_case(
    "nested_quantifiers",
    formulas=[
        "faculty_member(dr_john)", 
        "has_degree(dr_john, PhD)", 
        "higher(PhD, MSc)", 
        "higher(MSc, BA)",
        "ForAll(x, ForAll(d, (faculty_member(x) AND has_degree(x, d) AND higher(d, BA)) -> teach_undergrad(x)))"
    ],
)

# Test Case 4: Implication between quantified statements
run_case(
    "quantified_implication",
    formulas=[
        "(ForAll(x, (IsPreparingForExam(x) -> IsAskingQuestions(x))) -> ForAll(y, (NOT IsUnderstandingMaterial(y) -> NOT IsAttendingTutorials(y))))"
    ],
)

# Test Case 5: Unquantified implication
run_case(
    "plain_implication",
    formulas=["(Researching(x) -> ResearchCompleted(x))"],
)

# Test Case 6: NOT in antecedent
run_case(
    "not_implication",
    formulas=["NOT HasAccessToMaterials(x) -> NOT HasScholarship(x)"],
)

# Test Case 7: Biconditional
run_case(
    "biconditional",
    formulas=["ForAll(x, (A(x) <-> B(x)))"],
)

# Test Case 8: Malformed input (missing closing parenthesis)
run_parse_error_case(
    "missing_paren",
    formulas=["ForAll(x, (IsPreparingForExam(x) -> IsAskingQuestions(x))"],
)

# Test Case 9: Entailment (Socrates Syllogism - Valid)
socrates_premises = [
    "Human(Socrates)",
    "ForAll(x, (Human(x) -> Mortal(x)))"
]
assert check_entailment(socrates_premises, "Mortal(Socrates)") is True, "Socrates syllogism should be valid"

# Test Case 10: Entailment (Socrates Contradiction - Invalid/Not Entailed)
assert check_entailment(socrates_premises, "NOT Mortal(Socrates)") is False, "Negated Socrates syllogism should not be entailed"

# Test Case 11: Entailment (Plato - Not Entailed due to lack of information)
assert check_entailment(socrates_premises, "Mortal(Plato)") is False, "Plato's mortality is not entailed by Socrates premises"

print("All Z3 parser and entailment tests passed successfully.")