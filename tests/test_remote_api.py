import sys
import requests
import json

predict_url = "https://cqktgju--exact-api-server-api-server.modal.run/predict"

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

print(f"Sending Type 1 Request to {predict_url}...")
t1_resp = requests.post(predict_url, json=type1_payload, timeout=180)
print(f"Status Code: {t1_resp.status_code}")
if t1_resp.status_code == 200:
    print("Type 1 Response:")
    print(json.dumps(t1_resp.json(), indent=2))
else:
    print(t1_resp.text)

print(f"\nSending Type 2 Request to {predict_url}...")
t2_resp = requests.post(predict_url, json=type2_payload, timeout=180)
print(f"Status Code: {t2_resp.status_code}")
if t2_resp.status_code == 200:
    print("Type 2 Response:")
    print(json.dumps(t2_resp.json(), indent=2))
else:
    print(t2_resp.text)
