from logic.Z3_parser import prepare_z3_objects
from z3 import Solver, sat


def run_case(name: str, facts: list[str], rules: list[str], expect_sat: bool = True) -> None:
    symbols, fact_exprs, rule_exprs = prepare_z3_objects(facts, rules)
    solver = Solver()
    solver.add(*fact_exprs)
    solver.add(*rule_exprs)
    result = solver.check()
    if expect_sat:
        assert result == sat, f"{name} expected sat but got {result}"
    else:
        assert result != sat, f"{name} expected non-sat but got {result}"


def run_parse_error_case(name: str, facts: list[str], rules: list[str]) -> None:
    try:
        prepare_z3_objects(facts, rules)
    except ValueError:
        return
    raise AssertionError(f"{name} expected ValueError")


# Numeric-valued function comparisons
run_case(
    "numeric_comparison",
    facts=["active_status(sarah)", "completed_courses(sarah) = 4", "has_approval(sarah)"],
    rules=[
        "ForAll(x, (active_status(x) AND completed_courses(x) >= 5) -> eligible_advanced(x))",
        "ForAll(x, eligible_advanced(x) -> requires_approval(x))",
    ],
)

# Membership IN
run_case(
    "membership_in",
    facts=["alice IN group1"],
    rules=["ForAll(x, (x IN group1) -> member(x))"],
)

# Nested quantifiers
run_case(
    "nested_quantifiers",
    facts=["faculty_member(dr_john)", "has_degree(dr_john, PhD)", "higher(PhD, MSc)", "higher(MSc, BA)"],
    rules=[
        "ForAll(x, ForAll(d, (faculty_member(x) AND has_degree(x, d) AND higher(d, BA)) -> teach_undergrad(x)))"
    ],
)

# Implication between quantified statements
run_case(
    "quantified_implication",
    facts=[],
    rules=[
        "(ForAll(x, (IsPreparingForExam(x) -> IsAskingQuestions(x))) -> ForAll(y, (NOT IsUnderstandingMaterial(y) -> NOT IsAttendingTutorials(y))))"
    ],
)

# Unquantified implication
run_case(
    "plain_implication",
    facts=[],
    rules=["(Researching(x) -> ResearchCompleted(x))"],
)

# NOT in antecedent
run_case(
    "not_implication",
    facts=[],
    rules=["NOT HasAccessToMaterials(x) -> NOT HasScholarship(x)"],
)

# Biconditional
run_case(
    "biconditional",
    facts=[],
    rules=["ForAll(x, (A(x) <-> B(x)))"],
)

# Malformed input (missing closing parenthesis)
run_parse_error_case(
    "missing_paren",
    facts=[],
    rules=["ForAll(x, (IsPreparingForExam(x) -> IsAskingQuestions(x))"],
)

print("All Z3 parser tests passed.")