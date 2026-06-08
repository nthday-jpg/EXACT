import json
from pathlib import Path

log_path = Path(r"C:\Users\mduy\.gemini\antigravity-ide\brain\0d607334-a36c-4051-8bae-acc9504252ff\.system_generated\logs\transcript.jsonl")
if not log_path.exists():
    print("Log path does not exist")
    exit(1)

with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("type") == "USER_INPUT":
                print("USER:", data.get("content"))
                print("-" * 50)
            elif data.get("type") == "PLANNER_RESPONSE":
                content = data.get("content", "")
                if content:
                    print("ASSISTANT (first 2 lines):", "\n".join(content.split("\n")[:2]))
                    print("=" * 50)
        except Exception as e:
            pass
