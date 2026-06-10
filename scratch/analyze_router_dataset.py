import json
import collections

with open(r"d:\mduy\source\repos\EXACT\data\processed\router_dataset.json", "r", encoding="utf-8") as f:
    data = json.load(f)

domain_counts = collections.Counter()
multi_state_counts = collections.Counter()
num_domains_counts = collections.Counter()

for item in data:
    out = json.loads(item["output"])
    domains = out.get("domains", [])
    multi_state = out.get("multi_state", False)
    
    num_domains_counts[len(domains)] += 1
    for d in domains:
        domain_counts[d] += 1
    multi_state_counts[multi_state] += 1

print("--- Total Samples ---")
print(len(data))

print("\n--- Domain Distribution ---")
for d, count in domain_counts.most_common():
    print(f"{d}: {count} ({count/len(data)*100:.2f}%)")

print("\n--- Multi State Distribution ---")
for ms, count in multi_state_counts.items():
    print(f"{ms}: {count} ({count/len(data)*100:.2f}%)")

print("\n--- Number of Domains per Question Distribution ---")
for n, count in sorted(num_domains_counts.items()):
    print(f"{n} domains: {count} ({count/len(data)*100:.2f}%)")
