"""Backward-compatibility wrapper for Z3 verifier.
Delegates to the new modular package under src.logic.reasoning.verifier.
"""

from src.logic.reasoning.verifier import (
    Z3Symbols,
    TokenStream,
    FolParser,
    parse_formulas,
    verify_with_z3
)

__all__ = [
    "Z3Symbols",
    "TokenStream",
    "FolParser",
    "parse_formulas",
    "verify_with_z3"
]
