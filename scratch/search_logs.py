import json
import sys

# Ensure UTF-8 output even if Windows console defaults to cp1252
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

log_path = r"C:\Users\mduy\.gemini\antigravity-ide\brain\efa91464-cbcb-46f9-b0d8-adca4963257e\.system_generated\logs\transcript.jsonl"

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        content = obj.get("content", "")
        if "render" in content.lower() or "phương án" in content.lower():
            print(f"=== Step {obj.get('step_index')} ({obj.get('source')}) ===")
            print(content)
            print("-" * 80)
