import re

def balance_parentheses(text: str) -> str:
    text = text.strip()
    while True:
        depth = 0
        extra_found = False
        for i, char in enumerate(text):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth < 0:
                    # Extra closing paren! Remove it.
                    text = text[:i] + text[i+1:]
                    extra_found = True
                    break
        if not extra_found:
            break
            
    # Now balance any missing closing parentheses
    open_count = text.count("(")
    close_count = text.count(")")
    if close_count < open_count:
        text = text + ")" * (open_count - close_count)
        
    return text.strip()

def main():
    test_cases = [
        "ForAll(x, (WellTested(x) -> Optimized(x))))",
        "ForAll(x, (NOT FollowsPEP8(x)) -> NOT WellTested(x))))",
        "ForAll(x, EasyToMaintain(x)))",
        "ForAll(x, (FollowsPEP8(x)) -> EasyToMaintain(x))))",
        "ForAll(p, NOT WellStructuredPythonProject(p)) -> NOT FollowsPEP8PythonProject(p))))",
        "ForAll(x, ForAll(y, P(x, y)))",  # valid
    ]
    
    for tc in test_cases:
        print(f"Original:  {tc}")
        balanced = balance_parentheses(tc)
        print(f"Balanced:  {balanced}")
        print(f"Valid?     {balanced.count('(') == balanced.count(')')}\n")

if __name__ == "__main__":
    main()
