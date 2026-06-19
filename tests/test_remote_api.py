import argparse
import json
import os
import sys
import time
from typing import Any

import requests


if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DEFAULT_PREDICT_URL = os.getenv(
    "EXACT_PREDICT_URL",
    "https://cqktgju--exact-api-server-api-server.modal.run/predict",
)
DEFAULT_REQUEST_TIMEOUT_SECONDS = float(
    os.getenv("EXACT_REMOTE_REQUEST_TIMEOUT_SECONDS", "180")
)
DEFAULT_TYPE1_BUDGET_SECONDS = float(
    os.getenv("EXACT_REMOTE_TYPE1_BUDGET_SECONDS", "55")
)
DEFAULT_TYPE2_BUDGET_SECONDS = float(
    os.getenv("EXACT_REMOTE_TYPE2_BUDGET_SECONDS", "55")
)


def _assert_contains(text: str, needle: str) -> None:
    if needle.lower() not in text.lower():
        raise AssertionError(f"Expected '{needle}' in explanation, got: {text}")


def _assert_response_schema(item: dict[str, Any], query_id: str) -> None:
    expected_keys = {
        "query_id",
        "answer",
        "unit",
        "explanation",
        "premises_used",
        "reasoning",
    }
    if set(item.keys()) != expected_keys:
        raise AssertionError(
            f"{query_id}: unexpected response keys {sorted(item.keys())}, "
            f"expected {sorted(expected_keys)}"
        )
    if item["query_id"] != query_id:
        raise AssertionError(
            f"{query_id}: response query_id mismatch: {item['query_id']}"
        )
    if not isinstance(item["answer"], str):
        raise AssertionError(f"{query_id}: answer must be a string")
    if not isinstance(item["unit"], str):
        raise AssertionError(f"{query_id}: unit must be a string")
    if not isinstance(item["explanation"], str):
        raise AssertionError(f"{query_id}: explanation must be a string")
    if not isinstance(item["premises_used"], list):
        raise AssertionError(f"{query_id}: premises_used must be a list")
    if item["reasoning"] is not None:
        if not isinstance(item["reasoning"], dict):
            raise AssertionError(f"{query_id}: reasoning must be an object or null")
        if set(item["reasoning"].keys()) != {"type", "steps"}:
            raise AssertionError(
                f"{query_id}: reasoning keys must be exactly ['type', 'steps']"
            )
        if not isinstance(item["reasoning"]["type"], str):
            raise AssertionError(f"{query_id}: reasoning.type must be a string")
        if not isinstance(item["reasoning"]["steps"], list):
            raise AssertionError(f"{query_id}: reasoning.steps must be a list")


def _run_case(
    predict_url: str,
    case: dict[str, Any],
    request_timeout_seconds: float,
) -> float:
    payload = case["payload"]
    query_id = payload["query_id"]
    started = time.perf_counter()
    response = requests.post(
        predict_url,
        json=payload,
        timeout=request_timeout_seconds,
    )
    duration_seconds = time.perf_counter() - started
    print(
        f"{case['name']}: status={response.status_code} duration={duration_seconds:.2f}s"
    )
    response.raise_for_status()

    data = response.json()
    if not isinstance(data, list) or len(data) != 1:
        raise AssertionError(f"{query_id}: expected single-item list, got: {data}")

    item = data[0]
    _assert_response_schema(item, query_id)
    if duration_seconds > case["max_duration_seconds"]:
        raise AssertionError(
            f"{query_id}: duration {duration_seconds:.2f}s exceeded budget "
            f"{case['max_duration_seconds']:.2f}s"
        )

    case["assert_result"](item, duration_seconds)
    return duration_seconds


def _warm_up_remote_type1(
    predict_url: str,
    request_timeout_seconds: float,
) -> None:
    warmup_payload = {
        "query_id": "WARMUP_T1_FACT_YES",
        "type": "type1",
        "query": "Is Student A eligible for graduation?",
        "premises": [
            "A student who has completed at least 120 credits is eligible for graduation.",
            "Student A has completed 125 credits.",
        ],
        "options": ["Yes", "No", "Uncertain"],
    }
    started = time.perf_counter()
    response = requests.post(
        predict_url,
        json=warmup_payload,
        timeout=request_timeout_seconds,
    )
    duration_seconds = time.perf_counter() - started
    print(
        f"warmup_type1: status={response.status_code} duration={duration_seconds:.2f}s"
    )
    response.raise_for_status()


def _type1_cases(type1_budget_seconds: float) -> list[dict[str, Any]]:
    return [
        {
            "name": "type1_simple_fact_yes",
            "max_duration_seconds": type1_budget_seconds,
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
            "assert_result": lambda item, _duration: (
                item["answer"] == "Yes"
                or (_raise("TEST_T1_FACT_YES: expected answer Yes"), False)
            )
            and (
                set(item["premises_used"]) == {0, 1}
                or (_raise("TEST_T1_FACT_YES: expected premises_used {0, 1}"), False)
            ),
        },
        {
            "name": "type1_t1_0024_support_query_no",
            "max_duration_seconds": type1_budget_seconds,
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
            "assert_result": lambda item, _duration: (
                item["answer"] == "No"
                or (_raise("T1_0024: expected answer No"), False)
            )
            and (
                len(item["premises_used"]) >= 3
                or (_raise("T1_0024: expected at least 3 premises_used"), False)
            ),
        },
        {
            "name": "type1_t1_0048_meta_uncertain",
            "max_duration_seconds": type1_budget_seconds,
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
            "assert_result": lambda item, _duration: (
                item["answer"] == "Uncertain"
                or (_raise("T1_0048: expected answer Uncertain"), False)
            )
            and (
                item["premises_used"] == [7]
                or (_raise("T1_0048: expected premises_used [7]"), False)
            ),
        },
        {
            "name": "type1_t1_0021_mcq_explanation_sync",
            "max_duration_seconds": type1_budget_seconds,
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
            "assert_result": lambda item, _duration: (
                item["answer"] == "A"
                or (_raise("T1_0021: expected answer A"), False)
            )
            and (_assert_contains(item["explanation"], "climate-controlled case") is None),
        },
        {
            "name": "type1_t1_0046_mcq_attribution",
            "max_duration_seconds": type1_budget_seconds,
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
            "assert_result": lambda item, _duration: (
                item["answer"] == "A"
                or (_raise("T1_0046: expected answer A"), False)
            )
            and (
                item["premises_used"] != [6]
                or (_raise("T1_0046: premises_used must not collapse to [6]"), False)
            ),
        },
        {
            "name": "type1_t1_0025_latency_regression",
            "max_duration_seconds": type1_budget_seconds,
            "payload": {
                "query_id": "T1_0025",
                "type": "type1",
                "query": "Based on the drone delivery rules, which conclusion is logically supported?\nA. MedKit-7 cannot be dispatched because the route is blocked\nB. MedKit-7 has launch approval\nC. MedKit-7 is eligible to use the aerial corridor\nD. MedKit-7 is not a priority package",
                "premises": [
                    "If a package is medical and weighs under 2 kilograms, then it receives priority delivery status.",
                    "If a package has priority delivery status and its route is clear, then it can be dispatched.",
                    "If a package can be dispatched and the weather is safe, then it is eligible to use the aerial corridor.",
                    "If a package is eligible to use the aerial corridor and an operator is assigned, then launch is approved.",
                    "If an emergency waiver is approved and an alternate route is mapped, then the route is clear.",
                    "The MedKit-7 package is medical.",
                    "The MedKit-7 package weighs under 2 kilograms.",
                    "An emergency waiver is approved for MedKit-7.",
                    "An alternate route is mapped for MedKit-7.",
                    "The weather is safe for MedKit-7.",
                ],
                "options": ["A", "B", "C", "D"],
            },
            "assert_result": lambda item, duration: (
                item["answer"] == "C"
                or (_raise("T1_0025: expected answer C"), False)
            ),
        },
    ]


def _type2_cases(type2_budget_seconds: float) -> list[dict[str, Any]]:
    return [
        {
            "name": "type2_series_resistance_sanity",
            "max_duration_seconds": type2_budget_seconds,
            "payload": {
                "query_id": "TEST_T2_0001",
                "type": "type2",
                "query": "Two resistors R1 = 50 ohm and R2 = 50 ohm are connected in series. Find the total resistance.",
                "premises": [],
                "options": [],
            },
            "assert_result": lambda item, _duration: (
                abs(float(item["answer"]) - 100.0) < 1e-6
                or (_raise("TEST_T2_0001: expected answer 100"), False)
            )
            and (
                item["unit"] in {"", "ohm"}
                or (_raise("TEST_T2_0001: expected unit '' or 'ohm'"), False)
            ),
        }
    ]


def _raise(message: str) -> None:
    raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Remote EXACT /predict smoke gate")
    parser.add_argument("--url", default=DEFAULT_PREDICT_URL)
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--type1-budget-seconds",
        type=float,
        default=DEFAULT_TYPE1_BUDGET_SECONDS,
    )
    parser.add_argument(
        "--type2-budget-seconds",
        type=float,
        default=DEFAULT_TYPE2_BUDGET_SECONDS,
    )
    parser.add_argument(
        "--skip-warmup",
        action="store_true",
        help="Skip the untimed Type 1 warm-up request before latency assertions.",
    )
    args = parser.parse_args()

    results: list[tuple[str, float]] = []
    cases = _type1_cases(args.type1_budget_seconds) + _type2_cases(
        args.type2_budget_seconds
    )
    print(f"Running remote smoke against {args.url}")
    if not args.skip_warmup:
        _warm_up_remote_type1(
            args.url,
            request_timeout_seconds=args.request_timeout_seconds,
        )

    for case in cases:
        duration_seconds = _run_case(
            args.url,
            case,
            request_timeout_seconds=args.request_timeout_seconds,
        )
        results.append((case["name"], duration_seconds))

    print("\nRemote smoke summary:")
    for name, duration_seconds in results:
        print(f"- {name}: {duration_seconds:.2f}s")

    print("\nAll remote smoke cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
