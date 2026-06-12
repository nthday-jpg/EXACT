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
    return re.sub(r"[^a-zA-Z0-9]", "", s_cleaned)


def extract_constants(fol_list):
    """
    Extracts leaf constants from FOL formulas by matching predicate arguments.
    Filters out logical connectives, quantifiers, and standard variables.
    """
    constants = set()
    variables = {"x", "y", "z", "w", "u", "v", "t", "s", "i", "j"}
    keywords = {"forall", "exists", "and", "or", "not"}

    # Match predicate applications like Pred(arg1, arg2...)
    # Captures arguments inside parentheses
    pattern = re.compile(r"\b(?!ForAll\b|Exists\b)[a-zA-Z0-9_-]+\(([^()]+)\)")

    for fol in fol_list:
        for match in pattern.finditer(fol):
            args_str = match.group(1)
            args = [a.strip() for a in args_str.split(",")]
            for arg in args:
                if not arg:
                    continue
                if arg in variables or arg.lower() in keywords or len(arg) <= 1:
                    continue
                constants.add(arg)

    return list(constants)


def extract_predicates(fol_list):
    """
    Extracts predicate names from FOL formulas.
    """
    predicates = set()
    reserved = {"forall", "exists", "and", "or", "not", "implies", "in", "equal", "iff"}
    # Match word-like identifiers followed by (
    pattern = re.compile(r"\b([a-zA-Z0-9_-]+)\(")
    for fol in fol_list:
        for match in pattern.finditer(fol):
            pred = match.group(1)
            if pred.lower() not in reserved and len(pred) > 1:
                predicates.add(pred)
    return list(predicates)


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
                    stripped = span.strip(".,;:?!\"'()[]{}«»“”‘’")
                    if stripped.lower().endswith("'s") or stripped.lower().endswith(
                        "’s"
                    ):
                        stripped = stripped[:-2]
                    elif stripped.endswith("'") or stripped.endswith("’"):
                        stripped = stripped[:-1]
                    matches.add(stripped)
    return list(matches)


def find_predicate_nl_matches(pred, nl_sentences):
    """
    Finds original natural language phrases that likely represent the predicate 'pred'.
    Handles camelCase, snake_case, and variations.
    """
    matches = set()
    # Split predicate by underscore or camel case
    parts = re.findall(r"[A-Za-z0-9]+", pred)
    candidates = []

    # Candidate 1: spaces instead of underscores
    candidates.append(pred.replace("_", " "))

    # Candidate 2: split camelcase
    camel_parts = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)", pred)
    if camel_parts:
        candidates.append(" ".join(camel_parts))

    candidates.extend(camel_parts)
    candidates.extend(parts)

    # Filter candidates to avoid matching common small words
    stop_words = {
        "has",
        "is",
        "are",
        "have",
        "do",
        "does",
        "did",
        "was",
        "were",
        "be",
        "been",
        "a",
        "an",
        "the",
        "and",
        "or",
        "not",
        "to",
        "in",
        "of",
        "for",
        "on",
        "with",
        "at",
        "by",
    }
    candidates = [c for c in candidates if c.lower() not in stop_words and len(c) > 2]

    for cand in candidates:
        clean_cand = clean_str(cand)
        for sentence in nl_sentences:
            words = sentence.split()
            n = len(words)
            for i in range(n):
                for j in range(i + 1, n + 1):
                    if j - i > 6:
                        continue
                    span = " ".join(words[i:j])
                    if clean_str(span) == clean_cand:
                        stripped = span.strip(".,;:?!\"'()[]{}«»“”‘’")
                        matches.add(stripped)
    return list(matches)


class EntityAnonymizer:
    """
    Handles data augmentation for NL -> FOL translation datasets using entity anonymization,
    predicate perturbation, and randomized perturbation.
    """

    def __init__(
        self,
        names_pool=None,
        letters_pool=None,
        fantasy_names_pool=None,
        fantasy_predicates_pool=None,
    ):
        self.names_pool = names_pool or [
            "Alice",
            "Bob",
            "Charlie",
            "David",
            "Emma",
            "Frank",
            "Grace",
            "Henry",
            "Ivy",
            "Jack",
            "Kate",
            "Liam",
            "Mia",
            "Noah",
            "Olivia",
            "Peter",
            "Quinn",
            "Ryan",
            "Sophia",
            "Thomas",
            "Ursula",
            "Victor",
            "William",
            "Xavier",
            "Yara",
            "Zach",
        ]
        self.letters_pool = letters_pool or [
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
            "Q",
            "R",
            "S",
            "T",
            "U",
            "V",
            "W",
            "X",
            "Y",
            "Z",
        ]
        self.fantasy_names_pool = fantasy_names_pool or [
            "Zylok",
            "Glipglop",
            "Gorgon",
            "Snorky",
            "Quibble",
            "Xeloda",
            "Pluto",
            "Vortex",
            "Zorblax",
            "Gromble",
            "Flapjack",
            "Wobble",
            "Blinky",
            "Sputter",
            "Clinker",
            "Fizzle",
            "Spike",
            "Nebula",
            "Cosmo",
            "Rogue",
            "Pixel",
            "Quark",
            "Nova",
            "Cipher",
            "Specter",
            "Gadget",
            "Zenzey",
            "Xylos",
        ]
        self.fantasy_predicates_pool = fantasy_predicates_pool or [
            "Blorp",
            "Gleep",
            "Zazz",
            "Frooz",
            "Sploosh",
            "Kazam",
            "Yip",
            "Wab",
            "Chirp",
            "Plonk",
            "Spiff",
            "Zot",
            "Futz",
            "Gronk",
            "Snerl",
            "Yowl",
            "Zibble",
            "Plip",
            "Squip",
            "Zong",
            "Wubble",
            "Glurpa",
        ]

    def anonymize_sample(self, sample, strategy="mix", variant_idx=0):
        """
        Anonymizes proper names, constants, and potentially predicates in a single sample.
        Supported strategies:
          - "letters": replace constants with capital letters (A, B, C...)
          - "names": replace constants with standard names (Alice, Bob...)
          - "perturbation": replace constants with fantasy names, AND replace predicates with fantasy predicates.
          - "mix": randomly choose between "letters", "names", or "perturbation"
        """
        nl_premises = list(sample.get("premises-NL", []))
        question = sample.get("question", "")
        fol_premises = list(sample.get("premises-FOL", []))

        # Seed local_random deterministically
        import hashlib

        prems_str = "".join(nl_premises) + "".join(fol_premises)
        seed_str = f"{prems_str}_var_{variant_idx}"
        seed_hash = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
        local_random = random.Random(seed_hash)

        # Handle strategy mixing
        chosen_strategy = strategy
        if strategy == "mix":
            chosen_strategy = local_random.choice(["letters", "names", "perturbation"])

        # Pools
        names = list(
            self.fantasy_names_pool
            if chosen_strategy == "perturbation"
            else self.names_pool
        )
        letters = list(self.letters_pool)
        preds_pool = list(self.fantasy_predicates_pool)

        local_random.shuffle(names)
        local_random.shuffle(letters)
        local_random.shuffle(preds_pool)

        constants = extract_constants(fol_premises)
        nl_replacements = []
        fol_replacements = []

        # 1. Anonymize/Perturb Constants
        for idx, c in enumerate(constants):
            matches = find_nl_matches(c, nl_premises + [question])
            if not matches:
                continue

            if chosen_strategy == "letters":
                new_nl_name = letters[idx % len(letters)]
                new_fol_name = new_nl_name.lower()
            else:
                new_nl_name = names[idx % len(names)]
                new_fol_name = new_nl_name.lower()

            # Numeric/Temporal constants
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

        # 2. Perturb Predicates if strategy is "perturbation"
        if chosen_strategy == "perturbation":
            predicates = extract_predicates(fol_premises)
            for idx, p in enumerate(predicates):
                p_matches = find_predicate_nl_matches(p, nl_premises + [question])
                if not p_matches:
                    continue

                new_pred_name = preds_pool[idx % len(preds_pool)]

                # Check original casing to match
                # E.g., if pred is Student, replace with Blorp. If it's student, replace with blorp.
                new_fol_pred = new_pred_name
                if p[0].islower():
                    new_fol_pred = new_pred_name[0].lower() + new_pred_name[1:]

                for pm in p_matches:
                    pm_new = new_pred_name
                    if pm[0].islower():
                        pm_new = pm_new.lower()
                    # Preserve suffix s/es for verbs/nouns
                    if pm.endswith("s") and not pm_new.endswith("s"):
                        pm_new += "s"
                    nl_replacements.append((pm, pm_new))

                fol_replacements.append((p, new_fol_pred))

        if not nl_replacements and not fol_replacements:
            return None

        # Sort NL replacements by length descending to avoid substring conflicts
        nl_replacements.sort(key=lambda x: len(x[0]), reverse=True)

        # Replace in natural language
        new_nl_premises = []
        for nl in nl_premises:
            new_nl = nl
            for orig, rep in nl_replacements:
                new_nl = re.sub(rf"\b{re.escape(orig)}\b", rep, new_nl)
            new_nl_premises.append(new_nl)

        new_question = question
        for orig, rep in nl_replacements:
            new_question = re.sub(rf"\b{re.escape(orig)}\b", rep, new_question)

        # Replace in FOL
        new_fol_premises = []
        for fol in fol_premises:
            new_fol = fol
            for orig, rep in fol_replacements:
                new_fol = re.sub(rf"\b{orig}\b", rep, new_fol)
            new_fol_premises.append(new_fol)

        # Build augmented sample
        augmented_sample = sample.copy()
        augmented_sample["premises-NL"] = new_nl_premises
        augmented_sample["premises-FOL"] = new_fol_premises
        augmented_sample["question"] = new_question

        # Update metadata
        orig_source = sample.get("dataset_source", "unknown")
        augmented_sample["dataset_source"] = (
            f"{orig_source}-augmented-{chosen_strategy}-var{variant_idx}"
        )

        if "example_id" in sample:
            augmented_sample["example_id"] = (
                f"{sample['example_id']}_aug_var{variant_idx}"
            )

        return augmented_sample
