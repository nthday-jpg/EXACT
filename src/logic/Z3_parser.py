"""Parse simple FOL strings into Z3 expressions.

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
)


_TOKEN_RE = re.compile(
	r"\s*(->|<->|AND|OR|NOT|IN|ForAll|Exists|>=|<=|!=|=|>|<|\(|\)|,|\d+\.\d+|\d+|'[^']*'|[A-Za-z_][A-Za-z0-9_]*)"
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


def prepare_z3_objects(
	facts: Iterable[str],
	rules: Iterable[str],
	sort_name: str = "U",
) -> Tuple[Z3Symbols, List[BoolRef], List[BoolRef]]:
	"""Parse lists of facts and rules into Z3 Bool expressions.

	Returns a tuple of (symbols, fact_exprs, rule_exprs).
	"""

	symbols = Z3Symbols(sort=DeclareSort(sort_name))
	parser = FolParser(symbols)

	fact_exprs: List[BoolRef] = [parser.parse(f) for f in facts]
	rule_exprs: List[BoolRef] = [parser.parse(r) for r in rules]

	return symbols, fact_exprs, rule_exprs
