from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from src.physics.router import QuestionClassification


class RPRegistry:
    """Load and assemble domain-specific reasoning policies with hierarchical structure:
    
    GLOBAL_ONTOLOGY -> DOMAIN_REASONING_POLICIES -> FEWSHOTS -> QUESTION
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
    
    def assemble_reasoning_policies(self, domains: List[str], include_fewshot: bool = True) -> str:
        """
        Assemble reasoning_policies following hierarchical structure:
        <reasoning_policies>
        ... domain-specific reasoning policies ...
        </reasoning_policies>
        
        <fewshots>
        ... few-shot examples for domains ...
        </fewshots>
        """
        sections = []
        
        # 2. Load domain-specific reasoning policies
        domain_policies = []
        for domain in domains:
            policy = self.load_reasoning_policy(domain)
            if policy:
                domain_policies.append(f"{policy}")
        
        if domain_policies:
            combined_policies = "\n\n".join(domain_policies)
            sections.append(f"<reasoning_policies>\n{combined_policies}\n</reasoning_policies>")
        
        # 3. Load few-shot examples
        if include_fewshot:
            fewshots = []
            for domain in domains [:2]:  
                fewshot = self.load_fewshot(domain)
                if fewshot:
                    fewshots.append(f"## {domain.upper()}\n{fewshot}")
            
            if fewshots:
                combined_fewshots = "\n\n".join(fewshots)
                sections.append(f"<fewshots>\n{combined_fewshots}\n</fewshots>")
        
        return "\n\n".join(sections).strip()
    

    
    def build_solver_prompt_from_classification(
        self, classification: QuestionClassification
    ) -> str:
        """Build solver prompt from router classification.
        
        Returns hierarchical prompt:
        <warning> -> <reasoning_policies> -> <fewshots>
        """
        reasoning_policies = self.assemble_reasoning_policies(classification.domains, include_fewshot=True)
        header = ""
        if classification.warnings:
            warning_text = "\n".join(classification.warnings)
            header = f"{header}\n\n<warning>\n{warning_text}\n</warning>"
        if reasoning_policies:
            return f"{header}\n\n{reasoning_policies}"
        return header


def get_solver_prompt(classification: QuestionClassification) -> str:
    """Build solver prompt from router classification for solver.
    
    Integrates with router output to provide hierarchical reasoning policies:
    REASONING_POLICIES -> FEWSHOTS
    
    Usage:
        classification = classify_question(question, model_name=..., api_key=...)
        solver_prompt = get_solver_prompt(classification)
        solver_result = run_solver(question, solver_prompt)
    """
    registry = RPRegistry()
    return registry.build_solver_prompt_from_classification(classification)
