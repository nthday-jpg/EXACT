"""Parse simple FOL strings into Z3 expressions and verify entailment.

Assumptions:
- Quantifiers use `ForAll(x, ...)` / `Exists(x, ...)`.
- Boolean operators: `AND`, `OR`, `NOT`, `->`, `<->`.
- Predicates are functions returning Bool, e.g., `P(x)` or `R(a,b)`.
- Comparisons supported: `=`, `!=`, `>=`, `<=`, `>`, `<`.

Delegates parsing logic to `src.logic.reasoning.parser` for clean modularity.
"""

from __future__ import annotations

import z3
from z3 import Solver, unsat, sat

# Import parsing classes and helper functions from modular parser
from src.logic.reasoning.parser import (
    Z3Symbols,
    TokenStream,
    FolParser,
    parse_formulas,
    try_parse_fol,
)

# Export all symbols for backward compatibility
__all__ = [
    "Z3Symbols",
    "TokenStream",
    "FolParser",
    "parse_formulas",
    "try_parse_fol",
    "verify_with_z3",
    "extract_proof_structure",
]

# Enable Z3 proof globally
z3.set_param('proof', True)


def verify_with_z3(premises_fol: list[str], conclusion_fol: str, negate_conclusion: bool = True) -> dict:
    """
    Parses First-Order Logic (FOL) formulas, tracks premises and the negated (or non-negated) conclusion
    in Z3 solver to obtain the minimal Unsatisfiable Core (unsat_core) or counterexample Model.
    
    Args:
        premises_fol: List of FOL strings representing the premises.
        conclusion_fol: FOL string representing the conclusion to check.
        negate_conclusion: Whether to negate the conclusion before adding to the solver.
        
    Returns:
        dict: A dictionary containing:
            - "result": z3.CheckResult (unsat, sat, or unknown)
            - "proof": z3.Expr representing the formal proof if unsat, else None
            - "unsat_core": List of string tracking variables (e.g. ['p_1', 'neg_conclusion'])
            - "model": z3.Model containing the counterexample if sat, else None
    """
    negated_conclusion_fol = f"NOT ({conclusion_fol})" if negate_conclusion else conclusion_fol
    all_formulas = premises_fol + [negated_conclusion_fol]
    
    try:
        try:
            symbols, exprs = parse_formulas(all_formulas)
        except Exception as e:
            # Fallback to standardizing common logical operators & balancing parentheses
            standardized_formulas = []
            for f_str in all_formulas:
                f_clean = f_str.replace("¬", "NOT ").replace("∧", " AND ").replace("∨", " OR ").replace("→", " -> ").replace("↔", " <-> ")
                open_count = f_clean.count("(")
                close_count = f_clean.count(")")
                if close_count < open_count:
                    f_clean = f_clean + ")" * (open_count - close_count)
                standardized_formulas.append(f_clean)
            symbols, exprs = parse_formulas(standardized_formulas)
    except Exception as parse_err:
        # Return a safe, graceful fallback instead of crashing the pipeline
        return {
            "result": z3.unknown,
            "proof": None,
            "unsat_core": [],
            "model": None,
            "error": f"Z3 parsing failed completely: {str(parse_err)}"
        }
        
    premise_exprs = exprs[:-1]
    negated_conclusion_expr = exprs[-1]
    
    solver = Solver()
    
    # Track premises for unsat core
    tracking_vars = []
    for idx, expr in enumerate(premise_exprs, 1):
        track_var = z3.Bool(f"p_{idx}")
        solver.assert_and_track(expr, track_var)
        tracking_vars.append(track_var)
        
    # Track negated conclusion for unsat core
    neg_c_var = z3.Bool("neg_conclusion")
    solver.assert_and_track(negated_conclusion_expr, neg_c_var)
	
    result = solver.check()
	
    verification_result = {
        "result": result,
        "proof": None,
        "unsat_core": [],
        "model": None
    }
	
    if result == unsat:
        verification_result["proof"] = solver.proof()
        core = solver.unsat_core()
        verification_result["unsat_core"] = [str(var) for var in core]
    elif result == sat:
        verification_result["model"] = solver.model()
		
    return verification_result


def extract_proof_structure(proof) -> str:
    """Traverses the Z3 proof tree and returns a clean, human-readable skeleton of proof steps."""
    if proof is None:
        return ""
	
    visited = set()
    steps = []
	
    def traverse(node):
        node_str = str(node)
        if node_str in visited:
            return
        visited.add(node_str)
		
        # Check if it is a Z3 application node before calling decl() to prevent Z3Exception
        if z3.is_app(node):
            rule = node.decl().name()
			
            # Post-order traversal to process children (dependencies) first
            for child in node.children():
                traverse(child)
				
            if rule == "asserted":
                # This represents a raw premise from our input
                fact = node.arg(0) if node.num_args() > 0 else node
                steps.append(f"- Premise used: {fact}")
            elif rule not in ("hypothesis", "asserted"):
                # This represents a logical deduction step
                fact = node.arg(0) if node.num_args() > 0 else "consequence"
                steps.append(f"- Deduction ({rule}): Derived '{fact}'")
        else:
            # Non-app nodes (like variables, quantifiers, etc.)
            for child in node.children():
                traverse(child)
			
    try:
        traverse(proof)
        # Cap the output to keep LLM context readable and prevent context bloat
        if len(steps) > 35:
            steps = steps[:5] + [f"... [Skipped {len(steps) - 15} intermediate deduction steps] ..."] + steps[-10:]
        return "\n".join(steps)
    except Exception as e:
        return f"Proof traversal error: {str(e)}"
