from __future__ import annotations

from typing import Optional, Protocol

from src.physics.types import PhysicsResult, PhysicsTask


class SelfCorrector(Protocol):
    def propose_fix(self, result: PhysicsResult) -> Optional[PhysicsTask]:
        """Return a revised task or None if no correction is available."""
        raise NotImplementedError
