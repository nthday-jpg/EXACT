import json
import re

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
    
    # Match predicate applications like Pred(arg1, arg2...)
    # We ignore ForAll and Exists
    # Group 1 is ([^()]+) because negative lookahead is non-capturing
    pattern = re.compile(r'\b(?!ForAll\b|Exists\b)[a-zA-Z0-9_-]+\(([^()]+)\)')
    
    for fol in fol_list:
        for match in pattern.finditer(fol):
            args_str = match.group(1)
            # Split args by comma
            args = [a.strip() for a in args_str.split(',')]
            for arg in args:
                if not arg:
                    continue
                # If it's a variable or keyword or single character, skip
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
                # Optimization: span length maximum 12 words
                if j - i > 12:
                    continue
                span = " ".join(words[i:j])
                cleaned_span = clean_str(span)
                if cleaned_span == clean_c:
                    stripped = span.strip(".,;:?!\"'")
                    matches.add(stripped)
    return list(matches)

# Let's load a few samples from merged_valid.json and test
merged_path = r"d:\mduy\source\repos\EXACT\data\processed\merged_valid.json"
with open(merged_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Loaded {len(data)} samples from merged_valid.json\n")

for idx, sample in enumerate(data[:15]):
    nl_list = sample["premises-NL"] + [sample["question"]]
    fol_list = sample["premises-FOL"]
    
    constants = extract_constants(fol_list)
    print(f"Sample {idx} (ID: {sample.get('example_id')})")
    print(f"  Extracted Constants: {constants}")
    
    mappings = {}
    for c in constants:
        matches = find_nl_matches(c, nl_list)
        if matches:
            mappings[c] = matches
        else:
            print(f"  [WARN] No match found for constant: {c}")
            
    print(f"  Mappings: {mappings}\n")
