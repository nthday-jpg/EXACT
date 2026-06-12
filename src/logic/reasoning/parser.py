"""Parse simple FOL strings into Z3 expressions.

Assumptions:
- Quantifiers use `ForAll(x, ...)` / `Exists(x, ...)`.
- Boolean operators: `AND`, `OR`, `NOT`, `->`, `<->`.
- Predicates are functions returning Bool, e.g., `P(x)` or `R(a,b)`.
- Comparisons supported: `=`, `!=`, `>=`, `<=`, `>`, `<`.
"""

from __future__ import annotations

import re
import threading
from typing import Dict, Iterable, List, Optional, Tuple

from z3 import (
    And,
    BoolSort,
    Const,
    DeclareSort,
    Exists,
    ForAll,
    Function,
    IntVal,
    Not,
    Or,
    RealSort,
    RealVal,
    StringVal,
    BoolRef,
    ExprRef,
)

_TOKEN_RE = re.compile(
    r"\s*(->|<->|AND|OR|NOT|IN|ForAll|Exists|>=|<=|!=|=|>|<|\(|\)|,|\+|-|\d+\.\d+|\d+|'[^']*'|[^\W\d][\w-]*)"
)


class Z3Symbols:
    def __init__(self, sort: ExprRef) -> None:
        self.sort = sort
        self.consts: Dict[str, ExprRef] = {}
        self.preds: Dict[Tuple[str, int], ExprRef] = {}
        self.funcs: Dict[Tuple[str, int], ExprRef] = {}
        self.numeric_symbols: set[str] = set()

    def get_const(self, name: str, sort: Optional[ExprRef] = None) -> ExprRef:
        if name in self.consts:
            return self.consts[name]
        use_sort = sort
        if use_sort is None:
            use_sort = RealSort() if name in self.numeric_symbols else self.sort
        const = Const(name, use_sort)
        self.consts[name] = const
        return const

    def get_pred(self, name: str, arity: int) -> ExprRef:
        key = (name, arity)
        if key in self.preds:
            return self.preds[key]
        # Upgrades predicates to RealSort functions if they are involved in comparisons
        if name in self.numeric_symbols:
            return self.get_func(name, arity, RealSort())
        pred = Function(name, *([self.sort] * arity), BoolSort())
        self.preds[key] = pred
        return pred

    def get_func(
        self, name: str, arity: int, sort: Optional[ExprRef] = None
    ) -> ExprRef:
        key = (name, arity)
        if key in self.funcs:
            return self.funcs[key]
        use_sort = sort
        if use_sort is None:
            use_sort = RealSort() if name in self.numeric_symbols else self.sort
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
        left = self._parse_simple_term(stream, prefer_numeric=prefer_numeric)
        while stream.peek() in ("+", "-"):
            op = stream.next()
            right = self._parse_simple_term(stream, prefer_numeric=True)
            if op == "+":
                left = left + right
            else:
                left = left - right
        return left

    def _parse_simple_term(
        self, stream: TokenStream, prefer_numeric: bool = False
    ) -> ExprRef:
        tok = stream.next()
        if tok is None:
            raise ValueError("Unexpected end of input")
        if tok == "(":
            expr = self._parse_term(stream, prefer_numeric=prefer_numeric)
            stream.expect(")")
            return expr
        if tok.startswith("'") and tok.endswith("'"):
            return StringVal(tok[1:-1])

        # Parse temporal time constants (e.g., Time830AM, Time500PM) as minutes since midnight
        time_match = re.match(r"^Time(\d{1,2})(\d{2})?(AM|PM)$", tok, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            ampm = time_match.group(3).upper()
            if ampm == "PM" and hour < 12:
                hour += 12
            elif ampm == "AM" and hour == 12:
                hour = 0
            minutes = hour * 60 + minute
            return IntVal(minutes)

        # Parse temporal durations (e.g., Duration4Hours, Duration30Minutes) as minutes
        duration_match = re.match(
            r"^Duration(\d+(?:\.\d+)?)(Hours|Minutes|Days)$", tok, re.IGNORECASE
        )
        if duration_match:
            value = float(duration_match.group(1))
            unit = duration_match.group(2).lower()
            if unit == "hours":
                minutes = int(value * 60)
            elif unit == "days":
                minutes = int(value * 24 * 60)
            else:
                minutes = int(value)
            return IntVal(minutes)

        if tok.replace(".", "", 1).isdigit():
            if prefer_numeric:
                if "." in tok:
                    return RealVal(tok)
                return IntVal(tok)
            return self.symbols.get_const(tok)
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
                func = self.symbols.get_func(tok, len(args), RealSort())
                return func(*args)
            pred = self.symbols.get_pred(tok, len(args))
            return pred(*args)
        if prefer_numeric:
            return self.symbols.get_const(tok, RealSort())
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
    # Robust pre-scan to identify numeric symbols and prevent sort mismatches
    numeric_symbols = set()
    for f in formulas:
        # Temporarily replace logical arrows to prevent false matching of '-' or '>'
        f_temp = f.replace("<->", " BICOND ").replace("->", " IMPLIES ")

        # 1. Match identifiers on the left of inequality or arithmetic operators
        left_matches = re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\([^()]*\))?\s*(?:>=|<=|>|<|\+|-)\b",
            f_temp,
        )
        for m in left_matches:
            name = m.group(1)
            if name not in (
                "ForAll",
                "Exists",
                "AND",
                "OR",
                "NOT",
                "IN",
                "BICOND",
                "IMPLIES",
            ):
                numeric_symbols.add(name)

        # 2. Match identifiers on the right of inequality or arithmetic operators
        right_matches = re.finditer(
            r"\b(?:>=|<=|>|<|\+|-)\s*([A-Za-z_][A-Za-z0-9_-]*)\b", f_temp
        )
        for m in right_matches:
            name = m.group(1)
            if name not in (
                "ForAll",
                "Exists",
                "AND",
                "OR",
                "NOT",
                "IN",
                "BICOND",
                "IMPLIES",
            ):
                numeric_symbols.add(name)

        # 3. Match equality/inequality with numeric or temporal/duration literals on either side
        eq_matches = re.finditer(
            r"\b([A-Za-z_][A-Za-z0-9_-]*)\s*(?:\([^()]*\))?\s*(?:=|!=)\s*(?:\d+(?:\.\d+)?|Time\d+[A-Za-z]+|Duration\d+[A-Z]+)\b",
            f_temp,
        )
        for m in eq_matches:
            name = m.group(1)
            if name not in (
                "ForAll",
                "Exists",
                "AND",
                "OR",
                "NOT",
                "IN",
                "BICOND",
                "IMPLIES",
            ):
                numeric_symbols.add(name)

        eq_rev_matches = re.finditer(
            r"\b(?:\d+(?:\.\d+)?|Time\d+[A-Za-z]+|Duration\d+[A-Z]+)\s*(?:=|!=)\s*([A-Za-z_][A-Za-z0-9_-]*)\b",
            f_temp,
        )
        for m in eq_rev_matches:
            name = m.group(1)
            if name not in (
                "ForAll",
                "Exists",
                "AND",
                "OR",
                "NOT",
                "IN",
                "BICOND",
                "IMPLIES",
            ):
                numeric_symbols.add(name)

    symbols = Z3Symbols(sort=DeclareSort(sort_name))
    symbols.numeric_symbols = numeric_symbols

    parser = FolParser(symbols)
    formula_exprs: List[BoolRef] = [parser.parse(f) for f in formulas]

    return symbols, formula_exprs


# Global lock to ensure thread-safe access to Z3 (which is not thread-safe by default)
_z3_lock = threading.Lock()


def try_parse_fol(formula: str) -> tuple[bool, str]:
    """Try to parse a single FOL formula string into a Z3 expression.

    Returns:
        (True, "")           if the formula parses successfully.
        (False, error_msg)   if the parser raises an exception.

    Used by the translation repair loop to validate each generated formula
    before committing it, without running a full solver check.
    """
    with _z3_lock:
        try:
            parse_formulas([formula])
            return True, ""
        except Exception as exc:
            return False, str(exc)
