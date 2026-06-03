import re
import random

def clean_str(s):
    """
    Cleans a string for matching by removing non-alphanumeric characters and lowercasing.
    Also strips temporal (yearXXXX) and numeric (numberXXXX) prefixes for matching original text digits.
    """
    s_cleaned = s.lower()
    if s_cleaned.endswith("'s") or s_cleaned.endswith("’s"):
        s_cleaned = s_cleaned[:-2]
    if s_cleaned.startswith("year") and s_cleaned[4:].isdigit():
        s_cleaned = s_cleaned[4:]
    elif s_cleaned.startswith("number") and s_cleaned[6:].isdigit():
        s_cleaned = s_cleaned[6:]
    return re.sub(r'[^a-zA-Z0-9]', '', s_cleaned)

def extract_constants(fol_list):
    """
    Extracts leaf constants from FOL formulas by matching predicate arguments.
    Filters out logical connectives, quantifiers, and standard variables.
    """
    constants = set()
    variables = {'x', 'y', 'z', 'w', 'u', 'v', 't', 's', 'i', 'j'}
    keywords = {'forall', 'exists', 'and', 'or', 'not'}
    
    # Match predicate applications like Pred(arg1, arg2...)
    # Group 1 is ([^()]+) which captures arguments inside parentheses
    pattern = re.compile(r'\b(?!ForAll\b|Exists\b)[a-zA-Z0-9_-]+\(([^()]+)\)')
    
    for fol in fol_list:
        for match in pattern.finditer(fol):
            args_str = match.group(1)
            # Split arguments by comma
            args = [a.strip() for a in args_str.split(',')]
            for arg in args:
                if not arg:
                    continue
                # Skip variables, keywords, or extremely short placeholders
                if arg in variables or arg.lower() in keywords or len(arg) <= 1:
                    continue
                constants.add(arg)
                
    return list(constants)

def find_nl_matches(c, nl_sentences):
    """
    Finds the exact original natural language phrase representing FOL constant 'c'
    by looking at sliding windows of words in the NL sentences.
    """
    matches = set()
    clean_c = clean_str(c)
    
    for sentence in nl_sentences:
        words = sentence.split()
        n = len(words)
        for i in range(n):
            for j in range(i + 1, n + 1):
                if j - i > 12:  # Optimize span width to avoid overly long matches
                    continue
                span = " ".join(words[i:j])
                cleaned_span = clean_str(span)
                if cleaned_span == clean_c:
                    # Strip leading/trailing punctuation, parentheses, brackets, and quotes before recording
                    stripped = span.strip(".,;:?!\"'()[]{}«»“”‘’")
                    # Strip possessive 's or ’s (and plural possessive ') to get the clean base name
                    if stripped.lower().endswith("'s") or stripped.lower().endswith("’s"):
                        stripped = stripped[:-2]
                    elif stripped.endswith("'") or stripped.endswith("’"):
                        stripped = stripped[:-1]
                    matches.add(stripped)
    return list(matches)


class EntityAnonymizer:
    """
    Handles data augmentation for NL -> FOL translation datasets using entity anonymization & permutation.
    """
    def __init__(self, names_pool=None, letters_pool=None):
        self.names_pool = names_pool or [
            "Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Henry", "Ivy", 
            "Jack", "Kate", "Liam", "Mia", "Noah", "Olivia", "Peter", "Quinn", "Ryan", 
            "Sophia", "Thomas", "Ursula", "Victor", "William", "Xavier", "Yara", "Zach"
        ]
        self.letters_pool = letters_pool or [
            "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", 
            "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"
        ]

    def anonymize_sample(self, sample, strategy="mix", variant_idx=0):
        """
        Anonymizes proper names and other constants in a single dataset sample.
        Allows generating multiple variants (e.g. 2-5 variants) using the variant_idx parameter.
        Returns a new augmented sample dictionary or None if no constants are found/matched.
        """
        nl_premises = list(sample.get("premises-NL", []))
        question = sample.get("question", "")
        fol_premises = list(sample.get("premises-FOL", []))
        
        constants = extract_constants(fol_premises)
        if not constants:
            return None
            
        # Seed local_random with a stable hash of premises combined with variant_idx
        # to ensure consistent anonymization for the same variant across different questions
        # belonging to the same story, while allowing different variants to have distinct entities.
        import hashlib
        prems_str = "".join(nl_premises) + "".join(fol_premises)
        seed_str = f"{prems_str}_var_{variant_idx}"
        seed_hash = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
        local_random = random.Random(seed_hash)

        # Determine strategy
        chosen_strategy = strategy
        if strategy == "mix":
            chosen_strategy = local_random.choice(["letters", "names"])
            
        # Shuffle pools to get randomized assignments
        names = list(self.names_pool)
        letters = list(self.letters_pool)
        local_random.shuffle(names)
        local_random.shuffle(letters)
        
        nl_replacements = []
        fol_replacements = []
        
        for idx, c in enumerate(constants):
            matches = find_nl_matches(c, nl_premises + [question])
            if not matches:
                continue
                
            # Assign replacement entity based on the chosen strategy
            if chosen_strategy == "letters":
                new_nl_name = letters[idx % len(letters)]
                new_fol_name = new_nl_name.lower()
            else:
                new_nl_name = names[idx % len(names)]
                new_fol_name = new_nl_name.lower()
                
            # Special handling for temporal (year) and numeric constants to keep them realistic
            if c.startswith("year") and c[4:].isdigit():
                rand_year = str(local_random.randint(1950, 2025))
                new_nl_name = rand_year
                new_fol_name = f"year{rand_year}"
            elif c.startswith("number") and c[6:].isdigit():
                rand_num = str(local_random.randint(10000, 99999))
                new_nl_name = rand_num
                new_fol_name = f"number{rand_num}"
                
            for m in matches:
                nl_replacements.append((m, new_nl_name))
            fol_replacements.append((c, new_fol_name))
            
        if not nl_replacements:
            return None
            
        # Sort NL replacements by original string length descending to replace larger phrases first
        nl_replacements.sort(key=lambda x: len(x[0]), reverse=True)
        
        # Replace entities in Natural Language sentences using safe word boundaries
        new_nl_premises = []
        for nl in nl_premises:
            new_nl = nl
            for orig, rep in nl_replacements:
                new_nl = re.sub(rf'\b{re.escape(orig)}\b', rep, new_nl)
            new_nl_premises.append(new_nl)
            
        new_question = question
        for orig, rep in nl_replacements:
            new_question = re.sub(rf'\b{re.escape(orig)}\b', rep, new_question)
            
        # Replace constants in FOL formulas using word boundary regex matching
        new_fol_premises = []
        for fol in fol_premises:
            new_fol = fol
            for orig, rep in fol_replacements:
                new_fol = re.sub(rf'\b{orig}\b', rep, new_fol)
            new_fol_premises.append(new_fol)
            
        # Build augmented sample
        augmented_sample = sample.copy()
        augmented_sample["premises-NL"] = new_nl_premises
        augmented_sample["premises-FOL"] = new_fol_premises
        augmented_sample["question"] = new_question
        
        # Update source metadata to trace augmented source
        orig_source = sample.get("dataset_source", "unknown")
        augmented_sample["dataset_source"] = f"{orig_source}-augmented-{chosen_strategy}-var{variant_idx}"
        
        if "example_id" in sample:
            augmented_sample["example_id"] = f"{sample['example_id']}_aug_var{variant_idx}"
            
        return augmented_sample
