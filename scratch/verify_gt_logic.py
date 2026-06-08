import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
sys.path.append(str(root))

import z3
from src.logic.reasoning.parser import parse_formulas

gt_premises = [
    "ForAll(x, (passed_vehicle_inspection(x) AND has_appropriate_license(x)) -> can_transport_standard_goods(x))",
    "ForAll(x, (can_transport_standard_goods(x) AND completed_hazmat_training(x) AND received_safety_endorsement(x)) -> can_transport_hazardous_materials(x))",
    "ForAll(x, (can_transport_hazardous_materials(x) AND has_interstate_permit(x)) -> can_cross_state_lines(x))",
    "passed_vehicle_inspection(john)",
    "has_appropriate_license(john)",
    "completed_hazmat_training(john)",
    "NOT received_safety_endorsement(john)",
    "has_interstate_permit(john)"
]

gt_opt_c = "NOT can_transport_hazardous_materials(john)"

symbols, premises_exprs = parse_formulas(gt_premises)
opt_sym, opt_exprs = parse_formulas([gt_opt_c])

solver = z3.Solver()
for p in premises_exprs:
    solver.add(p)
solver.add(z3.Not(opt_exprs[0]))
res = solver.check()
print("GT Option C Proven from GT Premises:", res == z3.unsat)
