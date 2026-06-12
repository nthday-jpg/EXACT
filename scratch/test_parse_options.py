import re

def parse_mcq_options_robust(text: str) -> dict[str, str]:
    options = {}
    
    # Improved regex pattern
    pattern = r"(?:\s+|^)(?:[\-\*]\s+)?(?:\(|\[|Option\s+)?([A-G])(?:\)|\]|\.|\:)?\s+(.*?)(?=\s+(?:[\-\*]\s+)?(?:\(|\[|Option\s+)?[A-G](?:\)|\]|\.|\:)?\s+|$)"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    for opt_char, opt_text in matches:
        options[opt_char.upper()] = opt_text.strip()
    
    if len(options) >= 2:
        return options
        
    # Pattern 2: line-by-line fallback
    options = {}
    lines = text.splitlines()
    current_key = None
    current_text = []
    for line in lines:
        m = re.match(r"^\s*(?:Option\s+)?(?:\(?|\[?)([A-G])(?:\)?|\]?)[\.\)\:\-]\s*(.*)$", line, re.IGNORECASE)
        if m:
            if current_key:
                options[current_key] = "\n".join(current_text).strip()
            current_key = m.group(1).upper()
            current_text = [m.group(2).strip()]
        else:
            if current_key:
                current_text.append(line.strip())
    if current_key:
        options[current_key] = "\n".join(current_text).strip()
        
    return options

# Test cases
test_cases = [
    "Which is true?\nA. Socrates is mortal\nB. Socrates is human\nC. Plato is mortal\nD. None of the above",
    "Which is true? (A) Socrates is mortal (B) Socrates is human (C) Plato is mortal (D) None of the above",
    "Which is true?\nOption A: Socrates is mortal\nOption B: Socrates is human",
    "Which is true?\n- A. Socrates is mortal\n- B. Socrates is human",
    "Which is true?\n[A] Socrates is mortal\n[B] Socrates is human",
    "A. Socrates is mortal. B. Socrates is human."
]

for i, tc in enumerate(test_cases, 1):
    print(f"--- Case {i} ---")
    print(f"Robust  : {parse_mcq_options_robust(tc)}")
