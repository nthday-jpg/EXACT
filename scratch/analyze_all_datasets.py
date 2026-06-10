import json
from transformers import AutoTokenizer
import collections
import numpy as np

tokenizer = AutoTokenizer.from_pretrained("model_cache")

# --- 1. ANALYZE ROUTER DATASET ---
print("================= ROUTER DATASET ANALYSIS =================")
with open("data/processed/router_dataset.json", "r", encoding="utf-8") as f:
    router_data = json.load(f)

with open("src/physics/instructions/router.md", "r", encoding="utf-8") as f:
    router_system_prompt = f.read().strip()

router_lengths = []
domain_counts = collections.Counter()
multi_state_counts = collections.Counter()
num_domains_counts = collections.Counter()

for item in router_data:
    inp = item["input"]
    out = item["output"]
    
    # Label analysis
    out_obj = json.loads(out)
    domains = out_obj.get("domains", [])
    multi_state = out_obj.get("multi_state", False)
    
    num_domains_counts[len(domains)] += 1
    for d in domains:
        domain_counts[d] += 1
    multi_state_counts[multi_state] += 1

    # Token length analysis
    messages = [
        {"role": "system", "content": router_system_prompt},
        {"role": "user", "content": f"<QUESTION>\n{inp.strip()}\n</QUESTION>"},
        {"role": "assistant", "content": out.strip()}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    tokens = tokenizer.encode(text)
    router_lengths.append(len(tokens))

print(f"Total Router Samples: {len(router_data)}")
print(f"Max Token Length: {max(router_lengths)}")
print(f"Min Token Length: {min(router_lengths)}")
print(f"Mean Token Length: {np.mean(router_lengths):.2f}")
print(f"95th Percentile: {np.percentile(router_lengths, 95)}")
print(f"99th Percentile: {np.percentile(router_lengths, 99)}")

print("\n--- Domain Class Distribution ---")
for d, count in domain_counts.most_common():
    print(f"  {d}: {count} ({count/len(router_data)*100:.2f}%)")

print("\n--- Multi-State Distribution ---")
for ms, count in multi_state_counts.items():
    print(f"  {ms}: {count} ({count/len(router_data)*100:.2f}%)")

print("\n--- Number of Domains per Sample ---")
for n, count in sorted(num_domains_counts.items()):
    print(f"  {n} domains: {count} ({count/len(router_data)*100:.2f}%)")


# --- 2. ANALYZE FOL DATASET ---
print("\n================= FOL DATASET ANALYSIS =================")
with open("data/processed/logic_merged_valid_augmented.json", "r", encoding="utf-8") as f:
    fol_data = json.load(f)

# System/user prompt templates
system_prompt_template = (
    "You convert natural-language premises into parser-safe first-order logic formulas.\n\n"
    "Output a STRICT valid JSON list of strings containing the first-order logic formulas in the exact order of the input premises.\n"
    "You must output EXACTLY the same number of formulas as the input premises. Do not skip any premises or merge them.\n\n"
    "ALLOWED OPERATORS:\n"
    "AND, OR, NOT, ->, <->, =, !=, >=, <=, >, <, ForAll, Exists\n\n"
    "QUANTIFIER RULES:\n"
    "Use nested quantifiers only. E.g., ForAll(x, ForAll(y, P(x,y)))\n\n"
    "NUMERICAL ATTRIBUTES & COMPARISONS:\n"
    "Represent numerical attributes (e.g., age, score, GPA, duration, credits) as functions mapping to a number, and compare using operators (=, !=, >=, <=, >, <).\n"
    "E.g., \"John has a GPA of 3.8\" -> GPA(john) = 3.8\n"
    "E.g., \"GPA is at least 3.5\" -> ForAll(x, GPA(x) >= 3.5 -> ...)\n"
    "Do NOT use binary predicates like GPA(john, 3.8).\n\n"
    "DOMAIN RESTRICTION RULE:\n"
    "Restrict the domain of quantified variables to the relevant category.\n"
    "E.g., \"All students are happy\" -> ForAll(x, Student(x) -> Happy(x))\n"
    "Do NOT write ForAll(x, Happy(x)).\n\n"
    "Return JSON only."
)

user_prompt_template = (
    "Convert the following {num_premises} premises into canonical first-order logic.\n\n"
    "Premises:\n"
    "{premises}\n\n"
    "Return a JSON list of exactly {num_premises} strings containing the formulas, in the exact same order."
)

fol_lengths = []
num_premises = []
aug_counts = collections.Counter()

for item in fol_data:
    nl_list = item.get("premises-NL", [])
    fol_list = item.get("premises-FOL", [])
    ds = str(item.get("dataset_source", ""))
    
    if "augmented" in ds:
        aug_counts["augmented"] += 1
    else:
        aug_counts["original"] += 1
        
    num_premises.append(len(nl_list))
    
    nl_content = ""
    for i, nl in enumerate(nl_list, start=1):
        nl_content += f"{i}. {nl}\n"
        
    user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
    assistant_response = json.dumps(fol_list, indent=2)
    
    messages = [
        {"role": "system", "content": system_prompt_template},
        {"role": "user", "content": user_prompt.strip()},
        {"role": "assistant", "content": assistant_response.strip()}
    ]
    
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    tokens = tokenizer.encode(text)
    fol_lengths.append(len(tokens))

print(f"Total FOL Samples: {len(fol_data)}")
print(f"Max Token Length: {max(fol_lengths)}")
print(f"Min Token Length: {min(fol_lengths)}")
print(f"Mean Token Length: {np.mean(fol_lengths):.2f}")
print(f"95th Percentile: {np.percentile(fol_lengths, 95)}")
print(f"99th Percentile: {np.percentile(fol_lengths, 99)}")

print("\n--- Source Type ---")
for k, v in aug_counts.items():
    print(f"  {k}: {v} ({v/len(fol_data)*100:.2f}%)")

print("\n--- Number of Premises per Sample ---")
premises_counter = collections.Counter(num_premises)
for n, count in sorted(premises_counter.items()):
    print(f"  {n} premises: {count} ({count/len(fol_data)*100:.2f}%)")
