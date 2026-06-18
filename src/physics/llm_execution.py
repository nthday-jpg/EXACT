from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, List, Set

import sympy as sp


# =========================
# Data structures
# =========================

@dataclass
class SolutionStep:
    step_number: int
    variable: str
    formula: str
    substitution: str
    result: Any
    unit: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "variable": self.variable,
            "formula": self.formula,
            "substitution": self.substitution,
            "result": str(self.result),
            "unit": self.unit,
            "description": self.description,
        }


@dataclass
class WorkedSolution:
    answer: Any = None
    unit: Optional[List[str]] = None

    given: Dict[str, Any] = field(default_factory=dict)
    steps: List[SolutionStep] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "unit": self.unit,
            "given": {k: str(v) for k, v in self.given.items()},
            "steps": [s.to_dict() for s in self.steps],
            "variables": {k: str(v) for k, v in self.variables.items()},
        }


@dataclass
class ExecutionResult:
    answers: Optional[list[Any]]
    units: Optional[list[str]]
    solution: WorkedSolution


# =========================
# AST analysis
# =========================

class AssignmentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.assignments: List[Tuple[str, int]] = []

    def visit_Assign(self, node: ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                self.assignments.append((t.id, node.lineno))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            self.assignments.append((node.target.id, node.lineno))
        self.generic_visit(node)


def _assignment_order(code: str) -> List[Tuple[str, int]]:
    try:
        tree = ast.parse(code)
        v = AssignmentVisitor()
        v.visit(tree)
        return v.assignments
    except Exception:
        return []


def _analyze(code: str) -> Tuple[Set[str], Dict[str, str]]:
    given: Set[str] = set()
    formulas: Dict[str, str] = {}

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                try:
                    value = node.value
                    formula = ast.unparse(value) if hasattr(ast, "unparse") else str(value)
                except Exception:
                    formula = ""

                is_const = isinstance(value, (ast.Constant, ast.Num))

                targets = node.targets if isinstance(node, ast.Assign) else [node.target]

                for t in targets:
                    if isinstance(t, ast.Name):
                        name = t.id
                        formulas[name] = formula
                        if is_const:
                            given.add(name)

    except Exception:
        pass

    return given, formulas


def _substitute(formula: str, values: Dict[str, Any]) -> str:
    try:
        expr = sp.sympify(formula)
        subs = {}

        for s in expr.free_symbols:
            name = str(s)
            if name in values:
                val = values[name]
                val_str = f"({val})" if isinstance(val, (int, float)) and val < 0 else str(val)
                subs[s] = sp.Symbol(val_str)

        return str(expr.subs(subs)) if subs else formula

    except Exception:
        return formula


# =========================
# Formatting
# =========================

def _format_answers(raw: Any, precision: int) -> Optional[list[Any]]:
    if raw is None:
        return None

    def fmt(v: Any):
        try:
            ev = sp.N(v)
            if ev.is_number:
                x = float(ev)
                if abs(x) < 1e-3 or abs(x) >= 1e4:
                    return f"{x:.{precision}e}"
                return f"{x:.{precision}g}"
        except Exception:
            pass
        return str(v)

    if isinstance(raw, list):
        return [fmt(v) for v in raw]

    return [fmt(raw)]


# =========================
# Core extractor
# =========================

def _extract_trace(code: str, vars: Dict[str, Any]) -> WorkedSolution:
    sol = WorkedSolution()

    reserved = {"sp", "sympy", "__builtins__", "ans", "unit", "units"}

    sol.variables = {
        k: v for k, v in vars.items()
        if k not in reserved and not k.startswith("_")
    }

    units = vars.get("units") or vars.get("unit") or {}
    desc = vars.get("descriptions") or vars.get("description") or {}

    given, formulas = _analyze(code)

    for k in given:
        if k in sol.variables:
            sol.given[k] = sol.variables[k]

    order = _assignment_order(code)

    step_id = 1

    for name, _ in order:
        if name in reserved or name in sol.given:
            continue
        if name not in sol.variables:
            continue

        step = SolutionStep(
            step_number=step_id,
            variable=name,
            formula=formulas.get(name, str(sol.variables[name])),
            substitution=_substitute(
                formulas.get(name, ""),
                sol.variables
            ),
            result=sol.variables[name],
            unit=units.get(name, ""),
            description=desc.get(name, ""),
        )

        sol.steps.append(step)
        step_id += 1

    sol.answer = vars.get("ans")
    sol.unit = vars.get("unit")

    return sol


# =========================
# Public API (ONLY FUNCTION YOU NEED)
# =========================

def execute_llm_code(
    model_content: str,
    *,
    precision: int = 4,
) -> ExecutionResult:
    """
    Execute LLM-generated physics code and return structured trace.
    """

    model_json = json.loads(model_content)
    code = model_json.get("python_code")

    if not code:
        return ExecutionResult(None, None, WorkedSolution())

    local_vars: Dict[str, Any] = {}

    exec(code, {"sp": sp, "sympy": sp}, local_vars)

    trace = _extract_trace(code, local_vars)

    return ExecutionResult(
        answers=_format_answers(local_vars.get("ans"), precision),
        units=local_vars.get("unit") or [""] ,
        solution=trace,
    )


