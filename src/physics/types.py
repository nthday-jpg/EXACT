from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PhysicsTask:
    question: str
    correct: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PhysicsResult:
    task: PhysicsTask
    model_answer: Optional[Dict[str, Any]]
    raw_response: str
    error: Optional[str]
    tokens: Optional[Dict[str, Any]]
    elapsed_s: float


@dataclass
class PhysicsEval:
    result: PhysicsResult
    is_correct: Optional[bool]
    reason: Optional[str]
