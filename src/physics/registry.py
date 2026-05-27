from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from src.physics.router import QuestionClassification


class HeuristicRegistry:
    """Load and assemble domain-specific heuristics with hierarchical structure:
    
    GLOBAL_ONTOLOGY -> DOMAIN_HEURISTICS -> FEWSHOTS -> QUESTION
    """
    
    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            # Default: physics folder
            base_path = Path(__file__).parent
        else:
            base_path = Path(base_path)
        
        self.base_path = base_path
        self.fewshot_dir = base_path / "fewshot"
        self.reasoning_dir = base_path / "reasoning_policies"
        self.ontology_dir = base_path / "global_ontology"
    
    
    def load_global_ontology(self) -> str:
        """Load global ontology (can be single file or per-domain)."""
        # First try single global file
        global_path = self.ontology_dir / "global.md"
        if global_path.exists():
            return global_path.read_text(encoding="utf-8")
        
        # Fall back to root-level global_ontology.md
        ontology_path = self.base_path / "global_ontology.md"
        if ontology_path.exists():
            return ontology_path.read_text(encoding="utf-8")
        
        return ""
    
    def load_fewshot(self, domain: str) -> str:
        """Load few-shot examples for a domain."""
        path = self.fewshot_dir / f"{domain}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""
    
    def load_reasoning_policy(self, domain: str) -> str:
        """Load reasoning policy for a domain."""
        path = self.reasoning_dir / f"{domain}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""
    
    def assemble_heuristics(self, domains: List[str], include_fewshot: bool = True) -> str:
        """
        Assemble heuristics following hierarchical structure:
        
        <global_ontology>
        ... global physics concepts and definitions ...
        </global_ontology>
        
        <domain_heuristics>
        ... domain-specific reasoning policies ...
        </domain_heuristics>
        
        <fewshots>
        ... few-shot examples for domains ...
        </fewshots>
        """
        sections = []
        
        # 1. Load global ontology (once at the top)
        global_ontology = self.load_global_ontology()
        if global_ontology:
            sections.append(f"<global_ontology>\n{global_ontology}\n</global_ontology>")
        
        # 2. Load domain-specific heuristics (reasoning policies)
        domain_heuristics = []
        for domain in domains:
            policy = self.load_reasoning_policy(domain)
            if policy:
                domain_heuristics.append(f"## {domain.upper()}\n{policy}")
        
        if domain_heuristics:
            combined_heuristics = "\n\n".join(domain_heuristics)
            sections.append(f"<domain_heuristics>\n{combined_heuristics}\n</domain_heuristics>")
        
        # 3. Load few-shot examples
        if include_fewshot:
            fewshots = []
            for domain in domains:
                fewshot = self.load_fewshot(domain)
                if fewshot:
                    fewshots.append(f"## {domain.upper()}\n{fewshot}")
            
            if fewshots:
                combined_fewshots = "\n\n".join(fewshots)
                sections.append(f"<fewshots>\n{combined_fewshots}\n</fewshots>")
        
        return "\n\n".join(sections).strip()
    

    
    def build_heuristic_prompt_from_classification(
        self, classification: QuestionClassification
    ) -> str:
        """Build heuristic prompt from router classification.
        
        Returns hierarchical prompt:
        GLOBAL_ONTOLOGY -> DOMAIN_HEURISTICS -> FEWSHOTS
        """
        heuristics = self.assemble_heuristics(classification.domains, include_fewshot=True)
        header = f"<question_type>\n{classification.question_type}\n</question_type>"
        if classification.warnings:
            warning_text = "\n".join(classification.warnings)
            header = f"{header}\n\n<warning>\n{warning_text}\n</warning>"
        if heuristics:
            return f"{header}\n\n{heuristics}"
        return header


def get_heuristic_prompt(classification: QuestionClassification) -> str:
    """Build heuristic prompt from router classification for solver.
    
    Integrates with router output to provide hierarchical heuristics:
    GLOBAL_ONTOLOGY -> DOMAIN_HEURISTICS -> FEWSHOTS
    
    Usage:
        classification = classify_question(question, model_name=..., api_key=...)
        heuristic_prompt = get_heuristic_prompt(classification)
        solver_result = run_solver(question, heuristic_prompt)
    """
    registry = HeuristicRegistry()
    return registry.build_heuristic_prompt_from_classification(classification)
