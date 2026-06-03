import random
import hashlib

class MultiPremisePermuter:
    """
    Handles Multi-Premise Permutation for data augmentation.
    Shuffles the order of premises both in `premises-NL` and `premises-FOL` arrays
    while maintaining strict index-to-index alignment.
    """
    def __init__(self, seed=None):
        self.seed = seed

    def permute_sample(self, sample, custom_seed=None, variant_idx=0):
        """
        Shuffles the order of premises in a single dataset sample.
        Only applied to stories with a sufficient number of premises (>= 4 premises)
        according to the production guidelines to avoid redundant data.
        Returns a new augmented sample dictionary, or None if permutation is not possible.
        """
        nl_premises = list(sample.get("premises-NL", []))
        fol_premises = list(sample.get("premises-FOL", []))
        
        n = len(nl_premises)
        # Enforce minimum of 4 premises constraint
        if n < 4 or len(fol_premises) != n:
            return None

        # Determine stable seed
        chosen_seed = custom_seed if custom_seed is not None else self.seed
        if chosen_seed is None:
            # Seed local_random with a stable hash of premises combined with variant_idx
            # to allow generating multiple distinct permutation variants (e.g. 2 variants)
            prems_str = "".join(nl_premises) + "".join(fol_premises)
            seed_str = f"{prems_str}_perm_{variant_idx}"
            chosen_seed = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
            
        local_random = random.Random(chosen_seed)
        
        # Generate permutation indices
        indices = list(range(n))
        local_random.shuffle(indices)
        
        # Check if the shuffled order is different from original
        if indices == list(range(n)):
            # If shuffle resulted in the exact same order, try to force a swap if n >= 2
            # by swapping the first and last elements
            indices[0], indices[-1] = indices[-1], indices[0]
            
        # Reorder lists based on permutation
        new_nl_premises = [nl_premises[i] for i in indices]
        new_fol_premises = [fol_premises[i] for i in indices]
        
        # Build augmented sample
        augmented_sample = sample.copy()
        augmented_sample["premises-NL"] = new_nl_premises
        augmented_sample["premises-FOL"] = new_fol_premises
        
        # Update source metadata to trace augmented source
        orig_source = sample.get("dataset_source", "unknown")
        augmented_sample["dataset_source"] = f"{orig_source}-augmented-permutation-var{variant_idx}"
        
        if "example_id" in sample:
            augmented_sample["example_id"] = f"{sample['example_id']}_perm_var{variant_idx}"
            
        return augmented_sample
