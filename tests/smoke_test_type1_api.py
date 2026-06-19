import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests


if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LOCAL_URL = os.getenv("EXACT_LOCAL_PREDICT_URL", "http://127.0.0.1:8080/predict")
DEFAULT_STARTUP_TIMEOUT_SECONDS = 240.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 180.0
DEFAULT_POLL_INTERVAL_SECONDS = 2.0


def _is_local_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.hostname in {"127.0.0.1", "localhost"}


def _start_local_server() -> subprocess.Popen:
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.api_server:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8080",
    ]
    return subprocess.Popen(cmd, cwd=str(ROOT_DIR))


def _openapi_url_from_predict_url(predict_url: str) -> str:
    base, _, _ = predict_url.rpartition("/")
    return f"{base}/openapi.json"


def _wait_for_server_ready(
    predict_url: str,
    server_process: subprocess.Popen,
    startup_timeout_seconds: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> None:
    openapi_url = _openapi_url_from_predict_url(predict_url)
    deadline = time.perf_counter() + startup_timeout_seconds

    while time.perf_counter() < deadline:
        if server_process.poll() is not None:
            raise RuntimeError(
                f"Local FastAPI server exited early with code {server_process.returncode}."
            )
        try:
            response = requests.get(openapi_url, timeout=5)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(poll_interval_seconds)

    raise TimeoutError(
        f"Local FastAPI server did not become ready within {startup_timeout_seconds:.0f}s."
    )


def _assert_contains(text: str, needle: str) -> None:
    if needle.lower() not in text.lower():
        raise AssertionError(f"Expected '{needle}' in explanation, got: {text}")


def run_smoke_test() -> int:
    predict_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOCAL_URL
    request_timeout_seconds = float(
        os.getenv("EXACT_LOCAL_REQUEST_TIMEOUT_SECONDS", DEFAULT_REQUEST_TIMEOUT_SECONDS)
    )
    startup_timeout_seconds = float(
        os.getenv("EXACT_LOCAL_STARTUP_TIMEOUT_SECONDS", DEFAULT_STARTUP_TIMEOUT_SECONDS)
    )
    server_process = None

    test_cases = [
        {
            "name": "simple_fact_yes",
            "payload": {
                "query_id": "TEST_T1_FACT_YES",
                "type": "type1",
                "query": "Is Student A eligible for graduation?",
                "premises": [
                    "A student who has completed at least 120 credits is eligible for graduation.",
                    "Student A has completed 125 credits.",
                ],
                "options": ["Yes", "No", "Uncertain"],
            },
            "assertions": lambda res: (
                res["answer"] == "Yes",
                set(res["premises_used"]) == {0, 1},
            ),
        },
        {
            "name": "support_query_no",
            "payload": {
                "query_id": "T1_0024",
                "type": "type1",
                "query": "Do the premises prove that the Atlas case can be formally closed?",
                "premises": [
                    "If a server is patched and its logs have been reviewed, then the incident is contained.",
                    "If an incident is contained and all affected passwords have been reset, then the affected account is secured.",
                    "If an affected account is secured and the forensic report has been submitted, then the case is audit-ready.",
                    "If a case is audit-ready and a manager signs off, then the case can be formally closed.",
                    "The Atlas server is patched.",
                    "The Atlas server logs have been reviewed.",
                    "All affected Atlas passwords have been reset.",
                    "The Atlas forensic report has been submitted.",
                ],
                "options": ["Yes", "No", "Uncertain"],
            },
            "assertions": lambda res: (
                res["answer"] == "No",
                len(res["premises_used"]) >= 3,
            ),
        },
        {
            "name": "meta_uncertain",
            "payload": {
                "query_id": "T1_0048",
                "type": "type1",
                "query": "Does Linh have pharmacy training?",
                "premises": [
                    "If a clinic volunteer has first-aid certification and completed patient privacy training, then the volunteer may assist at the triage desk.",
                    "If a volunteer may assist at the triage desk and has morning availability, then the volunteer is assigned to the morning triage shift.",
                    "Every volunteer assigned to the morning triage shift receives a blue access badge.",
                    "Linh has first-aid certification.",
                    "Linh completed patient privacy training.",
                    "Linh has morning availability.",
                    "The morning triage shift needs 3 volunteers.",
                    "No premise states that Linh has pharmacy training.",
                ],
                "options": ["Yes", "No", "Uncertain"],
            },
            "assertions": lambda res: (
                res["answer"] == "Uncertain",
                res["premises_used"] == [7],
            ),
        },
        {
            "name": "mcq_answer_explanation_sync",
            "payload": {
                "query_id": "T1_0021",
                "type": "type1",
                "query": "Based on the museum conservation rules, which conclusion is logically supported?\nA. The Amber Amulet must be displayed in a climate-controlled case\nB. The Amber Amulet cannot be placed on public display\nC. The Amber Amulet needs pest treatment before storage\nD. The Amber Amulet lacks a provenance certificate",
                "premises": [
                    "If an artifact has a humidity-control log and no pest-damage report, then it is storage-ready.",
                    "If an artifact is storage-ready and has a provenance certificate, then it is eligible for exhibition.",
                    "If an artifact is eligible for exhibition and has curator approval, then it can be placed on public display.",
                    "If an artifact is fragile, then it requires low-light protection.",
                    "If an artifact requires low-light protection and can be placed on public display, then it must be displayed in a climate-controlled case.",
                    "The Amber Amulet has a humidity-control log.",
                    "The Amber Amulet has no pest-damage report.",
                    "The Amber Amulet has a provenance certificate.",
                    "The Amber Amulet has curator approval.",
                    "The Amber Amulet is fragile.",
                ],
                "options": ["A", "B", "C", "D"],
            },
            "assertions": lambda res: (
                res["answer"] == "A",
                _assert_contains(res["explanation"], "climate-controlled case") is None,
            ),
        },
        {
            "name": "mcq_premises_not_single_irrelevant_fact",
            "payload": {
                "query_id": "T1_0046",
                "type": "type1",
                "query": "Which conclusion is supported by the clinic roster premises?\nA. Linh receives a blue access badge\nB. Linh has pharmacy training\nC. The morning triage shift needs 5 volunteers\nD. Linh cannot assist at the triage desk",
                "premises": [
                    "If a clinic volunteer has first-aid certification and completed patient privacy training, then the volunteer may assist at the triage desk.",
                    "If a volunteer may assist at the triage desk and has morning availability, then the volunteer is assigned to the morning triage shift.",
                    "Every volunteer assigned to the morning triage shift receives a blue access badge.",
                    "Linh has first-aid certification.",
                    "Linh completed patient privacy training.",
                    "Linh has morning availability.",
                    "The morning triage shift needs 3 volunteers.",
                ],
                "options": ["A", "B", "C", "D"],
            },
            "assertions": lambda res: (
                res["answer"] == "A",
                res["premises_used"] != [6],
            ),
        },
    ]

    try:
        if _is_local_url(predict_url):
            print("Starting local FastAPI server for Type 1 smoke test...")
            server_process = _start_local_server()
            print(
                f"Polling server readiness for up to {startup_timeout_seconds:.0f}s at "
                f"{_openapi_url_from_predict_url(predict_url)}"
            )
            _wait_for_server_ready(
                predict_url,
                server_process,
                startup_timeout_seconds=startup_timeout_seconds,
            )

        for case in test_cases:
            print(f"\nRunning {case['name']} against {predict_url}")
            print(json.dumps(case["payload"], indent=2, ensure_ascii=False))
            started = time.perf_counter()
            response = requests.post(
                predict_url,
                json=case["payload"],
                timeout=request_timeout_seconds,
            )
            duration_seconds = time.perf_counter() - started
            print(f"Status: {response.status_code} in {duration_seconds:.2f}s")
            response.raise_for_status()
            result_list = response.json()
            if not isinstance(result_list, list) or len(result_list) != 1:
                raise AssertionError(f"Expected single-item list, got: {result_list}")
            result = result_list[0]
            print(json.dumps(result, indent=2, ensure_ascii=False))
            for outcome in case["assertions"](result):
                if outcome is False:
                    raise AssertionError(
                        f"Assertions failed for {case['name']}: "
                        f"{json.dumps(result, ensure_ascii=False)}"
                    )

        print("\nAll Type 1 smoke tests passed.")
        return 0
    finally:
        if server_process is not None:
            print("\nShutting down local FastAPI server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()


if __name__ == "__main__":
    raise SystemExit(run_smoke_test())
