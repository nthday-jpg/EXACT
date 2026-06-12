import requests
url = "https://cqktgju--exact-api-server-api-server.modal.run/docs"
try:
    print(f"Sending GET request to {url}...")
    resp = requests.get(url, timeout=45)
    print(f"Status Code: {resp.status_code}")
    print(f"Response length: {len(resp.text)} bytes")
except Exception as e:
    print(f"Error: {e}")
