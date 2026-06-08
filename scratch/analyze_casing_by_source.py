import json
import re
import collections
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with open(root / "data" / "processed" / "logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    data = json.load(f)

sources = collections.defaultdict(lambda: {"snake": 0, "pascal": 0, "total": 0})
for item in data:
    source = item.get("dataset_source", "unknown")
    for fol in item.get("premises-FOL", []):
        sources[source]["total"] += 1
        calls = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", fol)
        for call in calls:
            if call in {"ForAll", "Exists", "AND", "OR", "NOT", "In", "implies", "BICOND", "IMPLIES"}:
                continue
            if "_" in call and call.islower():
                sources[source]["snake"] += 1
            elif call[0].isupper() and "_" not in call:
                sources[source]["pascal"] += 1

print("Predicate casing distribution by dataset source:")
for src, counts in sources.items():
    print(f"  {src}:")
    print(f"    Total formulas: {counts['total']}")
    print(f"    snake_case predicates: {counts['snake']}")
    print(f"    PascalCase predicates: {counts['pascal']}")
