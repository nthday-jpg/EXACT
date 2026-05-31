import re
import json

GENERIC_WORDS = {
    'project', 'projects', 'python', 'code', 'standard', 'standards',
    'rule', 'rules', 'requirement', 'requirements', 'practice', 'practices',
    'convention', 'conventions', 'protocol', 'protocols', 'specification', 'specifications',
    'constraint', 'constraints', 'condition', 'conditions', 'regulation', 'regulations',
    'policy', 'policies', 'guideline', 'guidelines', 'recommendation', 'recommendations',
    'system', 'systems', 'application', 'applications', 'program', 'programs'
}

RESERVED_WORDS = {'ForAll', 'Exists', 'AND', 'OR', 'NOT', 'implies', 'IN'}

def split_camel_snake(s: str) -> list[str]:
    parts = s.split('_')
    words = []
    for part in parts:
        camel_parts = re.findall(r'[A-Z]?[a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)', part)
        if camel_parts:
            words.extend(camel_parts)
        else:
            words.append(part)
    return words

def get_core_words(name: str) -> tuple[str, ...]:
    words = split_camel_snake(name)
    core = [w for w in words if w.lower() not in GENERIC_WORDS]
    if not core:
        core = words
    return tuple(w.lower() for w in core)

def unify_fol_predicates(formulas: list[str]) -> list[str]:
    # Extract all predicate names
    predicate_pattern = r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\('
    predicates = set()
    for f in formulas:
        matches = re.findall(predicate_pattern, f)
        for m in matches:
            if m not in RESERVED_WORDS:
                predicates.add(m)

    # Map each predicate to its standardized, generic-stripped PascalCase name
    mapping = {}
    for p in predicates:
        words = split_camel_snake(p)
        core = [w for w in words if w.lower() not in GENERIC_WORDS]
        if not core:
            core = words
        # Standardize to PascalCase (capitalize first letter of each word)
        canonical = "".join(w[0].upper() + w[1:] if len(w) > 0 else w for w in core)
        mapping[p] = canonical

    # Replace in formulas
    unified_formulas = []
    for f in formulas:
        new_f = f
        # Replace each predicate name cleanly using word boundaries
        # Sort keys by length descending to avoid partial replacement issues
        for name in sorted(mapping.keys(), key=len, reverse=True):
            canonical = mapping[name]
            if name != canonical:
                new_f = re.sub(rf'\b{name}\b', canonical, new_f)
        unified_formulas.append(new_f)

    return unified_formulas

def main():
    formulas = [
      "ForAll(x, (WellTested(x) -> Optimized(x))))",
      "ForAll(x, (NOT FollowsPEP8(x)) -> NOT WellTested(x))))",
      "ForAll(x, EasyToMaintain(x)))",
      "ForAll(x, WellTested(x)))",
      "ForAll(x, (FollowsPEP8(x)) -> EasyToMaintain(x))))",
      "ForAll(x, (WellTested(x)) -> FollowsPEP8(x))))",
      "ForAll(x, (WellStructuredProject(x)) -> OptimizedProject(x))))",
      "ForAll(x, (EasyToMaintainProject(x)) -> WellTestedProject(x))))",
      "ForAll(x, (OptimizedProject(x)) -> CleanReadableCodeProject(x))))",
      "ForAll(x, WellStructuredProject(x)))",
      "ForAll(x, CleanReadableCodeProject(x)))",
      "ExistsAtLeastOneBestPracticePythonProject())",
      "ExistsAtLeastOneOptimizedPythonProject())",
      "ForAll(p, NOT WellStructuredPythonProject(p)) -> NOT FollowsPEP8PythonProject(p))))"
    ]

    print("--- Initial ---")
    for idx, f in enumerate(formulas, 1):
        print(f"{idx}. {f}")

    unified = unify_fol_predicates(formulas)

    print("\n--- Unified ---")
    for idx, f in enumerate(unified, 1):
        print(f"{idx}. {f}")

if __name__ == "__main__":
    main()
