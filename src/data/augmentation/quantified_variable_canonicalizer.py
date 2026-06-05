import re

class QuantifiedVariableCanonicalizer:
    """
    Handles Quantified Variable Canonicalization for data preprocessing/normalization.
    Systematically renames all bound variables in each FOL formula to a standard sequence
    (x, y, z, w, u, v, t, s) based on their order of appearance in each formula.
    This is treated as a mandatory 100% preprocessing step according to the production plan.
    """
    def __init__(self, canonical_sequence=None):
        self.canonical_sequence = canonical_sequence or ['x', 'y', 'z', 'w', 'u', 'v', 't', 's']

    def canonicalize_formula(self, fol):
        """
        Canonicalizes a single FOL formula string.
        """
        # Find all bound variables in order of appearance
        # Regex matches ForAll(var, ...) or Exists(var, ...)
        quantifier_pattern = re.compile(r'\b(ForAll|Exists)\(\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*,')
        
        seen_vars = []
        for match in quantifier_pattern.finditer(fol):
            var = match.group(2)
            if var not in seen_vars:
                seen_vars.append(var)
                
        if not seen_vars:
            return fol

        # Map each variable to its canonical counterpart
        mapping = {}
        for idx, var in enumerate(seen_vars):
            canonical_var = self.canonical_sequence[idx % len(self.canonical_sequence)]
            mapping[var] = canonical_var
            
        # If no changes are needed, return as is
        if all(k == v for k, v in mapping.items()):
            return fol

        # Use temporary placeholders to avoid intermediate variable collisions during replacement
        temp_mapping = {var: f"__TEMP_CANON_{idx}__" for idx, var in enumerate(mapping.keys())}
        
        new_fol = fol
        # Replace original variables with placeholders
        for orig, temp in temp_mapping.items():
            new_fol = re.sub(rf'\b{orig}\b', temp, new_fol)
        # Replace placeholders with canonical names
        for orig, temp in temp_mapping.items():
            new_fol = re.sub(rf'\b{temp}\b', mapping[orig], new_fol)
            
        return new_fol

    def canonicalize_sample(self, sample, always_return=True):
        """
        Canonicalizes bound variables in all FOL formulas of a single sample.
        Returns a new canonicalized sample. If always_return is False, returns None if no changes were made.
        """
        fol_premises = list(sample.get("premises-FOL", []))
        
        new_fol_premises = []
        changed = False
        for fol in fol_premises:
            canon_fol = self.canonicalize_formula(fol)
            if canon_fol != fol:
                changed = True
            new_fol_premises.append(canon_fol)
            
        if not changed:
            return sample.copy() if always_return else None
            
        # Build canonicalized sample
        canonicalized_sample = sample.copy()
        canonicalized_sample["premises-FOL"] = new_fol_premises
        
        # Update source metadata
        orig_source = sample.get("dataset_source", "unknown")
        if not orig_source.endswith("-canonicalized"):
            canonicalized_sample["dataset_source"] = f"{orig_source}-canonicalized"
        
        if "example_id" in sample and not sample["example_id"].endswith("_canonical"):
            canonicalized_sample["example_id"] = f"{sample['example_id']}_canonical"
            
        return canonicalized_sample
