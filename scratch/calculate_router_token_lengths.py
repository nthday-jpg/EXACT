import json
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("model_cache")

with open("src/physics/instructions/router.md", "r", encoding="utf-8") as f:
    router_system_prompt = f.read().strip()

with open("data/processed/router_dataset.json", "r", encoding="utf-8") as f:
    data = json.load(f)

lengths = []
for item in data:
    inp = item["input"]
    out = item["output"]
    
    messages = [
        {"role": "system", "content": router_system_prompt},
        {"role": "user", "content": f"<QUESTION>\n{inp.strip()}\n</QUESTION>"},
        {"role": "assistant", "content": out.strip()}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    tokens = tokenizer.encode(text)
    lengths.append(len(tokens))

print("Total samples:", len(lengths))
print("Max length (tokens):", max(lengths))
print("Min length (tokens):", min(lengths))
print("Mean length (tokens):", sum(lengths)/len(lengths))
# Print 95th and 99th percentiles
lengths.sort()
print("95th percentile:", lengths[int(len(lengths)*0.95)])
print("99th percentile:", lengths[int(len(lengths)*0.99)])
