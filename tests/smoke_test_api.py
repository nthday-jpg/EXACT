import sys
import time
import subprocess
import requests
import json
from pathlib import Path

# Reconfigure stdout/stderr to use UTF-8 to prevent CP1252 UnicodeEncodeError on Windows
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

def run_smoke_test():
    print("Starting FastAPI server in a subprocess...")
    # Start uvicorn server on localhost:8080 and let its output go directly to console
    cmd = [sys.executable, "-m", "uvicorn", "src.api_server:app", "--host", "127.0.0.1", "--port", "8080"]
    server_process = subprocess.Popen(
        cmd,
        cwd=str(root_dir)
    )
    
    # Wait for the server to start up and log initialization
    print("Waiting 45 seconds for pipelines to initialize...")
    time.sleep(45)
    
    predict_url = "http://127.0.0.1:8080/predict"
    
    # Define test samples
    type1_payload = {
        "query_id": "TEST_T1_0001",
        "type": "type1",
        "query": "Is Student A eligible for graduation?",
        "premises": [
            "A student who has completed at least 120 credits is eligible for graduation.",
            "Student A has completed 125 credits."
        ],
        "options": ["Yes", "No", "Uncertain"]
    }
    
    type2_payload = {
        "query_id": "TEST_T2_0001",
        "type": "type2",
        "query": "Two resistors R1 = 50 ohm and R2 = 50 ohm are connected in series. Find the total resistance.",
        "premises": [],
        "options": []
    }
    
    failed = False
    
    try:
        # 1. Test Type 1
        print("\nSending Type 1 Request...")
        print(json.dumps(type1_payload, indent=2))
        t1_start = time.time()
        t1_resp = requests.post(predict_url, json=type1_payload, timeout=180)
        t1_elapsed = time.time() - t1_start
        print(f"Status Code: {t1_resp.status_code} (took {t1_elapsed:.2f}s)")
        
        if t1_resp.status_code == 200:
            results = t1_resp.json()
            print("Response:")
            print(json.dumps(results, indent=2))
            
            # Assertions
            assert isinstance(results, list), "Response must be a list"
            assert len(results) == 1, "Response list must contain exactly 1 item"
            res = results[0]
            assert res.get("query_id") == "TEST_T1_0001"
            assert res.get("answer") == "Yes", f"Expected 'Yes', got {res.get('answer')}"
            assert res.get("unit") == ""
            assert isinstance(res.get("premises_used"), list)
            assert 0 in res.get("premises_used") and 1 in res.get("premises_used")
            assert "explanation" in res and res.get("explanation")
            print("🟢 Type 1 validation passed!")
        else:
            print(f"🔴 Type 1 Request failed with status {t1_resp.status_code}")
            print(t1_resp.text)
            failed = True
            
        # 2. Test Type 2
        print("\nSending Type 2 Request...")
        print(json.dumps(type2_payload, indent=2))
        t2_start = time.time()
        t2_resp = requests.post(predict_url, json=type2_payload, timeout=180)
        t2_elapsed = time.time() - t2_start
        print(f"Status Code: {t2_resp.status_code} (took {t2_elapsed:.2f}s)")
        
        if t2_resp.status_code == 200:
            results = t2_resp.json()
            print("Response:")
            print(json.dumps(results, indent=2))
            
            # Assertions
            assert isinstance(results, list), "Response must be a list"
            assert len(results) == 1, "Response list must contain exactly 1 item"
            res = results[0]
            assert res.get("query_id") == "TEST_T2_0001"
            assert res.get("answer") == "100", f"Expected '100', got {res.get('answer')}"
            assert res.get("unit") in ("ohm", "Ω", "Ohm"), f"Expected ohm, got {res.get('unit')}"
            assert res.get("premises_used") == []
            assert "explanation" in res and res.get("explanation")
            print("🟢 Type 2 validation passed!")
        else:
            print(f"🔴 Type 2 Request failed with status {t2_resp.status_code}")
            print(t2_resp.text)
            failed = True

    except Exception as e:
        print(f"🔴 Test execution error: {str(e)}")
        import traceback
        traceback.print_exc()
        failed = True
    finally:
        print("\nShutting down FastAPI server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("FastAPI server terminated cleanly.")
        except subprocess.TimeoutExpired:
            print("Force killing FastAPI server...")
            server_process.kill()
            
    if failed:
        sys.exit(1)
    else:
        print("\n🏆 All smoke tests passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    run_smoke_test()
