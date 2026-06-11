import os
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

def main():
    model_id = "d:/mduy/source/repos/EXACT/model_cache"
    adapter_id = "d:/mduy/source/repos/EXACT/results"
    val_path = "d:/mduy/source/repos/EXACT/data/processed/logic_merged_valid_augmented.json"

    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Loading base model in 4-bit...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4"
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config,
        device_map="auto"
    )

    print("Loading Peft adapter...")
    model = PeftModel.from_pretrained(base_model, adapter_id)
    model.eval()

    print(f"Loading validation samples from {val_path}...")
    with open(val_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    val_samples = [s for s in data if s.get("split") == "val"]
    print(f"Total val samples found: {len(val_samples)}")

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

    # Let's test the first 5 validation samples
    for idx, item in enumerate(val_samples[:5]):
        print("\n" + "="*80)
        print(f"Sample {idx+1} (ID: {item.get('example_id')})")
        nl_list = item["premises-NL"]
        fol_list_gt = item["premises-FOL"]

        print("Premises NL:")
        for i, nl in enumerate(nl_list, start=1):
            print(f"  {i}. {nl}")

        nl_content = ""
        for i, nl in enumerate(nl_list, start=1):
            nl_content += f"{i}. {nl}\n"

        user_prompt = user_prompt_template.format(num_premises=len(nl_list), premises=nl_content.strip())
        messages = [
            {"role": "system", "content": system_prompt_template},
            {"role": "user", "content": user_prompt.strip()}
        ]

        prompt_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt_text, return_tensors="pt").to("cuda")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=1024,
                do_sample=False,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

        print("\nRaw Response:")
        print(response)

        # Parse and print side-by-side
        try:
            # Simple clean JSON response (similar to clean_json_response in notebook)
            import re
            cleaned = response.strip()
            if cleaned.startswith("```"):
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
                if match:
                    cleaned = match.group(1)
            parsed = json.loads(cleaned)
            print("\nComparison (GT vs Pred):")
            for gt, pred in zip(fol_list_gt, parsed):
                match_status = "MATCH" if gt.strip() == pred.strip() else "MISMATCH"
                print(f"  [{match_status}]")
                print(f"    GT  : {gt}")
                print(f"    Pred: {pred}")
        except Exception as e:
            print(f"\nFailed to parse JSON response: {e}")

if __name__ == "__main__":
    main()
