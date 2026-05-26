"""Parse simple FOL strings into Z3 expressions and verify entailment.

Assumptions:
- Quantifiers use `ForAll(x, ...)` / `Exists(x, ...)`.
- Boolean operators: `AND`, `OR`, `NOT`, `->`, `<->`.
- Predicates are functions returning Bool, e.g., `P(x)` or `R(a,b)`.
- Comparisons supported: `=`, `!=`, `>=`, `<=`, `>`, `<`.

This is a lightweight parser for baseline reasoning tasks. It is not a full
FOL or arithmetic parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, Iterable, List, Optional, Tuple

import z3
from z3 import (
	And,
	BoolSort,
	Const,
	DeclareSort,
	Exists,
	ForAll,
	Function,
	IntSort,
	IntVal,
	Not,
	Or,
	RealVal,
	StringSort,
	StringVal,
	BoolRef,
	ExprRef,
	Solver,
	unsat,
	sat,
)

_TOKEN_RE = re.compile(
	r"\s*(->|<->|AND|OR|NOT|IN|ForAll|Exists|>=|<=|!=|=|>|<|\(|\)|,|\d+\.\d+|\d+|'[^']*'|[^\W\d][\w-]*)"
)


@dataclass
class Z3Symbols:
	sort: ExprRef
	consts: Dict[str, ExprRef] = field(default_factory=dict)
	preds: Dict[Tuple[str, int], ExprRef] = field(default_factory=dict)
	funcs: Dict[Tuple[str, int], ExprRef] = field(default_factory=dict)

	def get_const(self, name: str, sort: Optional[ExprRef] = None) -> ExprRef:
		if name in self.consts:
			return self.consts[name]
		use_sort = sort or self.sort
		const = Const(name, use_sort)
		self.consts[name] = const
		return const

	def get_pred(self, name: str, arity: int) -> ExprRef:
		key = (name, arity)
		if key in self.preds:
			return self.preds[key]
		pred = Function(name, *([self.sort] * arity), BoolSort())
		self.preds[key] = pred
		return pred

	def get_func(self, name: str, arity: int, sort: Optional[ExprRef] = None) -> ExprRef:
		key = (name, arity)
		if key in self.funcs:
			return self.funcs[key]
		use_sort = self.sort if sort is None else sort
		func = Function(name, *([self.sort] * arity), use_sort)
		self.funcs[key] = func
		return func


class TokenStream:
	def __init__(self, text: str) -> None:
		self.tokens = [t for t in _TOKEN_RE.findall(text) if t.strip()]
		self.index = 0

	def peek(self) -> Optional[str]:
		if self.index >= len(self.tokens):
			return None
		return self.tokens[self.index]

	def peek_offset(self, offset: int) -> Optional[str]:
		idx = self.index + offset
		if idx >= len(self.tokens):
			return None
		return self.tokens[idx]

	def next(self) -> Optional[str]:
		tok = self.peek()
		if tok is not None:
			self.index += 1
		return tok

	def expect(self, value: str) -> None:
		tok = self.next()
		if tok != value:
			raise ValueError(f"Expected '{value}', got '{tok}'")


class FolParser:
	def __init__(self, symbols: Z3Symbols) -> None:
		self.symbols = symbols
		self.var_stack: List[Dict[str, ExprRef]] = []

	def parse(self, text: str) -> BoolRef:
		stream = TokenStream(text)
		expr = self._parse_implication(stream)
		return expr

	def _parse_implication(self, stream: TokenStream) -> BoolRef:
		left = self._parse_or(stream)
		tok = stream.peek()
		if tok == "->":
			stream.next()
			right = self._parse_implication(stream)
			return Or(Not(left), right)
		if tok == "<->":
			stream.next()
			right = self._parse_implication(stream)
			return And(Or(Not(left), right), Or(Not(right), left))
		return left

	def _parse_or(self, stream: TokenStream) -> BoolRef:
		left = self._parse_and(stream)
		while stream.peek() == "OR":
			stream.next()
			right = self._parse_and(stream)
			left = Or(left, right)
		return left

	def _parse_and(self, stream: TokenStream) -> BoolRef:
		left = self._parse_not(stream)
		while stream.peek() == "AND":
			stream.next()
			right = self._parse_not(stream)
			left = And(left, right)
		return left

	def _parse_not(self, stream: TokenStream) -> BoolRef:
		if stream.peek() == "NOT":
			stream.next()
			return Not(self._parse_not(stream))
		return self._parse_atom(stream)

	def _parse_atom(self, stream: TokenStream) -> BoolRef:
		tok = stream.peek()
		if tok is None:
			raise ValueError("Unexpected end of input")
		if tok == "(":
			stream.next()
			expr = self._parse_implication(stream)
			stream.expect(")")
			return expr
		if tok in ("ForAll", "Exists"):
			return self._parse_quantifier(stream)
		start_index = stream.index
		term = self._parse_term(stream)
		comp = stream.peek()
		if comp == "IN":
			stream.next()
			right = self._parse_term(stream)
			pred = self.symbols.get_pred("In", 2)
			return pred(term, right)
		if comp in ("=", "!=", ">=", "<=", ">", "<"):
			numeric = comp in (">=", "<=", ">", "<")
			if comp in ("=", "!="):
				next_tok = stream.peek_offset(1)
				if next_tok is not None and re.fullmatch(r"\d+(?:\.\d+)?", next_tok):
					numeric = True
			if numeric and isinstance(term, BoolRef):
				stream.index = start_index
				term = self._parse_term(stream, prefer_numeric=True)
				comp = stream.peek()
			stream.next()
			right = self._parse_term(stream, prefer_numeric=numeric)
			return self._build_comparison(comp, term, right)
		if not isinstance(term, BoolRef):
			raise ValueError("Predicate expected, got term")
		return term

	def _parse_quantifier(self, stream: TokenStream) -> BoolRef:
		quant = stream.next()
		stream.expect("(")
		var_name = stream.next()
		if var_name is None:
			raise ValueError("Missing quantified variable")
		stream.expect(",")
		var = Const(var_name, self.symbols.sort)
		self.var_stack.append({var_name: var})
		body = self._parse_implication(stream)
		self.var_stack.pop()
		stream.expect(")")
		if quant == "ForAll":
			return ForAll([var], body)
		return Exists([var], body)

	def _parse_term(self, stream: TokenStream, prefer_numeric: bool = False) -> ExprRef:
		tok = stream.next()
		if tok is None:
			raise ValueError("Unexpected end of input")
		if tok == "(":
			expr = self._parse_term(stream, prefer_numeric=prefer_numeric)
			stream.expect(")")
			return expr
		if tok.startswith("'") and tok.endswith("'"):
			return StringVal(tok[1:-1])
		if tok.replace(".", "", 1).isdigit():
			if "." in tok:
				return RealVal(tok)
			return IntVal(tok)
		var = self._lookup_var(tok)
		if var is not None:
			return var
		if stream.peek() == "(":
			stream.next()
			args = []
			if stream.peek() != ")":
				while True:
					args.append(self._parse_term(stream, prefer_numeric=prefer_numeric))
					if stream.peek() == ",":
						stream.next()
						continue
					break
			stream.expect(")")
			if prefer_numeric:
				func = self.symbols.get_func(tok, len(args), IntSort())
				return func(*args)
			pred = self.symbols.get_pred(tok, len(args))
			return pred(*args)
		if prefer_numeric:
			return self.symbols.get_const(tok, IntSort())
		return self.symbols.get_const(tok)

	def _build_comparison(self, op: str, left: ExprRef, right: ExprRef) -> BoolRef:
		if op == "=":
			return left == right
		if op == "!=":
			return left != right
		if op == ">=":
			return left >= right
		if op == "<=":
			return left <= right
		if op == ">":
			return left > right
		if op == "<":
			return left < right
		raise ValueError(f"Unsupported comparator: {op}")

	def _lookup_var(self, name: str) -> Optional[ExprRef]:
		for scope in reversed(self.var_stack):
			if name in scope:
				return scope[name]
		return None


def parse_formulas(
	formulas: Iterable[str],
	sort_name: str = "U",
) -> Tuple[Z3Symbols, List[BoolRef]]:
	"""Parse a flat list of first-order logic formulas into Z3 Bool expressions.

	Returns a tuple of (symbols, formula_exprs).
	"""

	symbols = Z3Symbols(sort=DeclareSort(sort_name))
	parser = FolParser(symbols)
	formula_exprs: List[BoolRef] = [parser.parse(f) for f in formulas]

	return symbols, formula_exprs


# Enable Z3 proof globally
z3.set_param('proof', True)


def verify_with_z3(premises_fol: list[str], conclusion_fol: str) -> dict:
	"""
	Parses First-Order Logic (FOL) formulas, tracks premises and the negated conclusion
	in Z3 solver to obtain the minimal Unsatisfiable Core (unsat_core) or counterexample Model.
	
	Args:
		premises_fol: List of FOL strings representing the premises.
		conclusion_fol: FOL string representing the conclusion to check.
		
	Returns:
		dict: A dictionary containing:
			- "result": z3.CheckResult (unsat, sat, or unknown)
			- "proof": z3.Expr representing the formal proof if unsat, else None
			- "unsat_core": List of string tracking variables (e.g. ['p_1', 'neg_conclusion'])
			- "model": z3.Model containing the counterexample if sat, else None
	"""
	negated_conclusion_fol = f"NOT ({conclusion_fol})"
	all_formulas = premises_fol + [negated_conclusion_fol]
	
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
