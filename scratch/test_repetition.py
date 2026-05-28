import os
import sys
from pathlib import Path
from dotenv import load_dotenv

if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

root_dir = Path(__file__).resolve().parents[1]
sys.path.append(str(root_dir))

from src.llm.llm_client import LLMClient

def main():
    load_dotenv()
    
    modal_url = "https://cqktgju--exact-qwen3-8b-lora-exactmodel-api-server.modal.run"
    base_url = f"{modal_url.rstrip('/')}/v1"
    model_name = "exact-qwen3-8b"
    api_key = os.getenv("MODAL_API_KEY") or "modal-placeholder"
    
    print(f"Connecting to {base_url}...")
    
    # Let's test different parameters to find the one that stops repetition!
    configs = [
        {"name": "Default (Low Temp)", "temp": 0.1, "fp": 0.0, "stop": None},
        {"name": "With Frequency Penalty 0.3", "temp": 0.1, "fp": 0.3, "stop": ["<|im_end|>", "<|endoftext|>"]},
        {"name": "With Frequency Penalty 0.5", "temp": 0.1, "fp": 0.5, "stop": ["<|im_end|>", "<|endoftext|>"]},
    ]
    
    system_prompt = (
        "You are an expert in logical reasoning. Your role is to explain arguments the way a knowledgeable human teacher would — "
        "through clear numbered steps that DERIVE new insights, not restate known facts.\n\n"
        "IMPORTANT RULES:\n"
        "- Each 'Step N:' must advance the reasoning chain with a new deduction or inference.\n"
        "- Synthesize across premises: show how they combine to produce a new conclusion.\n"
        "- Use transitional language: 'Since', 'Therefore', 'This means', 'Combined with', 'It follows that'.\n"
        "- Never copy a premise verbatim as a step — interpret and derive from it."
    )
    
    user_prompt = (
        "The following premises have been formally proven (via Z3 SMT solver) to entail the conclusion.\n\n"
        "Key premises:\n"
        "- Premise 5: Professor John has completed pedagogical training.\n"
        "- Premise 6: Professor John holds a PhD.\n"
        "- Premise 7: Professor John has published at least 3 academic papers.\n"
        "- Premise 8: Professor John has received a positive teaching evaluation.\n\n"
        "Conclusion:\n"
        "- Professor John meets all requirements to propose new courses.\n\n"
        "Write a numbered step-by-step explanation that traces the logical chain from premises to conclusion. "
        "Each step should build on the previous one and show a new deduction or inference — "
        "NOT simply restate a premise. Use transitions like 'Since', 'Therefore', 'This means', 'It follows that'. "
        "Format: 'Step N: <explanation>'."
    )
    
    for cfg in configs:
        print(f"\n==================================================")
        print(f"Testing Config: {cfg['name']}")
        
        client = LLMClient(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=cfg["temp"],
            use_local=False,
        )
        
        # Override frequency penalty and stop tokens in the client call
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": cfg["temp"],
                "max_tokens": 1024,
            }
            if cfg["fp"] > 0.0:
                kwargs["frequency_penalty"] = cfg["fp"]
            if cfg["stop"]:
                kwargs["stop"] = cfg["stop"]
                
            response = client.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            print(f"Finish Reason: {finish_reason}")
            print(f"Response length: {len(content)} chars")
            print("Response preview (first 400 chars):")
            print(content[:400] + "...")
            if len(content) > 400:
                print("Response preview (last 200 chars):")
                print("..." + content[-200:])
        except Exception as e:
            print("Error:", str(e))

if __name__ == "__main__":
    main()
