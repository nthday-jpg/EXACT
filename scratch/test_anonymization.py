import json
import re
import random

def clean_str(s):
    s_cleaned = s.lower()
    if s_cleaned.startswith("year") and s_cleaned[4:].isdigit():
        s_cleaned = s_cleaned[4:]
    elif s_cleaned.startswith("number") and s_cleaned[6:].isdigit():
        s_cleaned = s_cleaned[6:]
    return re.sub(r'[^a-zA-Z0-9]', '', s_cleaned)

def extract_constants(fol_list):
    constants = set()
    variables = {'x', 'y', 'z', 'w', 'u', 'v', 't', 's', 'i', 'j'}
    keywords = {'forall', 'exists', 'and', 'or', 'not'}
    pattern = re.compile(r'\b(?!ForAll\b|Exists\b)[a-zA-Z0-9_-]+\(([^()]+)\)')
    
    for fol in fol_list:
        for match in pattern.finditer(fol):
            args_str = match.group(1)
            args = [a.strip() for a in args_str.split(',')]
            for arg in args:
                if not arg:
                    continue
                if arg in variables or arg.lower() in keywords or len(arg) <= 1:
                    continue
                constants.add(arg)
    return list(constants)

def find_nl_matches(c, nl_sentences):
    matches = set()
    clean_c = clean_str(c)
    
    for sentence in nl_sentences:
        words = sentence.split()
        n = len(words)
        for i in range(n):
            for j in range(i + 1, n + 1):
                if j - i > 12:
                    continue
                span = " ".join(words[i:j])
                cleaned_span = clean_str(span)
                if cleaned_span == clean_c:
                    stripped = span.strip(".,;:?!\"'")
                    matches.add(stripped)
    return list(matches)

def anonymize_sample(sample, strategy="mix"):
    nl_premises = list(sample["premises-NL"])
    question = sample["question"]
    fol_premises = list(sample["premises-FOL"])
    
    constants = extract_constants(fol_premises)
    if not constants:
        return None  # Nothing to anonymize
        
    # Decide on strategy
    chosen_strategy = strategy
    if strategy == "mix":
        chosen_strategy = random.choice(["letters", "names"])
        
    names_pool = ["Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Henry", "Ivy", "Jack", "Kate", "Liam", "Mia", "Noah", "Olivia", "Peter", "Quinn", "Ryan", "Sophia", "Thomas", "Ursula", "Victor", "William", "Xavier", "Yara", "Zach"]
    letters_pool = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]
    
    random.shuffle(names_pool)
    random.shuffle(letters_pool)
    
    nl_replacements = []
    fol_replacements = []
    
    for idx, c in enumerate(constants):
        matches = find_nl_matches(c, nl_premises + [question])
        if not matches:
            continue
            
        # Determine replacement names based on strategy
        if chosen_strategy == "letters":
            new_nl_name = letters_pool[idx % len(letters_pool)]
            new_fol_name = new_nl_name.lower()
        else:
            new_nl_name = names_pool[idx % len(names_pool)]
            new_fol_name = new_nl_name.lower()
            
        # For years/numbers, we can preserve their numeric nature or just replace with random years/numbers
        if c.startswith("year") and c[4:].isdigit():
            # Generate a random year
            rand_year = str(random.randint(1950, 2025))
            new_nl_name = rand_year
            new_fol_name = f"year{rand_year}"
        elif c.startswith("number") and c[6:].isdigit():
            # Generate a random number
            rand_num = str(random.randint(10000, 99999))
            new_nl_name = rand_num
            new_fol_name = f"number{rand_num}"
            
        for m in matches:
            nl_replacements.append((m, new_nl_name))
        fol_replacements.append((c, new_fol_name))
        
    if not nl_replacements:
        return None
        
    # Sort NL replacements by length of original string descending to avoid partial matches
    nl_replacements.sort(key=lambda x: len(x[0]), reverse=True)
    
    # Replace in NL premises and question
    new_nl_premises = []
    for nl in nl_premises:
        new_nl = nl
        for orig, rep in nl_replacements:
            # We can use regex with word boundary or simple replace if word boundary doesn't match punctuation
            # To be super safe and preserve formatting, let's use re.sub with word boundary for words,
            # or simple replacement if it's multiple words.
            # Simple replace is actually extremely safe if we sort by length descending!
            new_nl = new_nl.replace(orig, rep)
        new_nl_premises.append(new_nl)
        
    new_question = question
    for orig, rep in nl_replacements:
        new_question = new_question.replace(orig, rep)
        
    # Replace in FOL formulas
    new_fol_premises = []
    for fol in fol_premises:
        new_fol = fol
        for orig, rep in fol_replacements:
            # Use word boundaries in regex for exact token matching
            new_fol = re.sub(rf'\b{orig}\b', rep, new_fol)
        new_fol_premises.append(new_fol)
        
    augmented_sample = sample.copy()
    augmented_sample["premises-NL"] = new_nl_premises
    augmented_sample["premises-FOL"] = new_fol_premises
    augmented_sample["question"] = new_question
    # We should distinguish augmented samples by story_id or example_id or dataset_source
    augmented_sample["dataset_source"] = f"{sample['dataset_source']}-augmented"
    if "example_id" in sample:
        augmented_sample["example_id"] = f"{sample['example_id']}_aug"
        
    return augmented_sample

# Let's test it on a few samples
merged_path = r"d:\mduy\source\repos\EXACT\data\processed\merged_valid.json"
with open(merged_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for idx in [4, 10, 13]:
    sample = data[idx]
    print(f"\n================ ORIGINAL SAMPLE {idx} ================")
    print(json.dumps(sample, indent=2))
    
    aug_letters = anonymize_sample(sample, "letters")
    print(f"\n================ AUGMENTED (LETTERS) ================")
    print(json.dumps(aug_letters, indent=2))
    
    aug_names = anonymize_sample(sample, "names")
    print(f"\n================ AUGMENTED (NAMES) ================")
    print(json.dumps(aug_names, indent=2))
