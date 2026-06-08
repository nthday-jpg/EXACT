import json
import re

def main():
    with open('data/logic_based.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Total raw samples: {len(data)}")
    
    stop_words = {
        'If', 'The', 'Students', 'A', 'B', 'C', 'D', 'ForAll', 'Exists', 'AND', 'OR', 'NOT',
        'There', 'In', 'On', 'At', 'For', 'To', 'From', 'By', 'With', 'As', 'Under', 'According',
        'When', 'Is', 'Are', 'An', 'This', 'No', 'Yes', 'So', 'However', 'Another', 'Each', 'All',
        'Both', 'Some', 'One', 'Two', 'Three', 'Four', 'Five', 'Every', 'Student', 'Regular',
        'Summer', 'Fall', 'Year', 'June', 'May', 'October', 'November', 'December', 'GPA', 'TOEFL',
        'IELTS', 'VND', 'History', 'MOSWord', 'MOSExcel', 'Seminar', 'Report', 'PhD', 'MSc', 'RegularProgram'
    }
    
    mismatched = []
    for idx, d in enumerate(data):
        nl_str = ' '.join(d.get('premises-NL', []))
        fol_str = ' '.join(d.get('premises-FOL', []))
        
        # Extract unique names/entities from NL
        names = set(re.findall(r'\b[A-Z][A-Za-z]+\b', nl_str))
        names = {n for n in names if n not in stop_words}
        
        # If none of the names found in NL are in FOL, it's a major sign of mismatch
        if names and not any(n.lower() in fol_str.lower() for n in names):
            mismatched.append({
                "idx": idx,
                "names": list(names),
                "fol": d.get("premises-FOL")[:2] if d.get("premises-FOL") else []
            })
            
    print(f"Found {len(mismatched)} mismatched raw samples after filtering stop words.")
    if mismatched:
        print("Mismatched raw samples first 3 details:")
        print(json.dumps(mismatched[:3], indent=2))

if __name__ == '__main__':
    main()
