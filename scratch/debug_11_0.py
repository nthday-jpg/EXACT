import sys
from pathlib import Path
import re

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

try:
    import z3
    from src.logic.reasoning.parser import parse_formulas
except ImportError as e:
    print("Import error:", e)
    sys.exit(1)

def test_formulas(formulas):
    print("Testing formulas:", formulas)
    try:
        symbols, exprs = parse_formulas(formulas)
        print("Parsed successfully!")
        for expr in exprs:
            print("  -", expr)
        return True, ""
    except Exception as e:
        print("Parsing failed with error:", e)
        return False, str(e)

print("--- Testing Case 11_0 ---")
formulas_11_0 = [
  "CompletedSafetyOrientation(alex)",
  "MembershipDuration(alex, 8)",
  "PaidAnnualFee(alex)",
  "ForAll(x, (ValidMembershipCard(x) AND CompletedSafetyOrientation(x) -> CanUseEquipment(x)))",
  "ForAll(x, (CanUseEquipment(x) AND HasTrainer(x) -> CanBookTraining(x)))",
  "ForAll(x, (MembershipDuration(x, 6) -> EligibleForTrainer(x)))",
  "ForAll(x, (PaidAnnualFee(x) -> ValidMembershipCard(x)))"
]
test_formulas(formulas_11_0)
