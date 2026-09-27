"""
test_chat_endpoint.py — Test /api/ai/chat endpoint directly via HTTP.
"""

import json
import sys
import time
import urllib.error
import urllib.request

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    url = f"{base_url.rstrip('/')}/api/ai/chat"
    token = "kai5108_secret_passcode_2026"
    message = sys.argv[2] if len(sys.argv) > 2 else "как подготовится к итиоп"
    model_param = sys.argv[3] if len(sys.argv) > 3 else "gemini-3.7-flash"

    req_data = {"message": message}
    if model_param:
        req_data["model"] = model_param
    payload = json.dumps(req_data).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "KaiTestClient/1.0",
    }

    print("=" * 80)
    print("      TESTING /api/ai/chat ENDPOINT")
    print("=" * 80)
    print(f"[*] Target URL:  {url}")
    print(f"[*] Message:     {message}")
    print(f"[*] Model Req:   {model_param}")
    print(f"[*] Auth Token:  {token[:8]}***")
    print("-" * 80)

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=70) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            elapsed = time.perf_counter() - t0

            print(f"[+] HTTP Status: {status_code} (took {elapsed:.2f}s)")
            data = json.loads(response_body)

            print("=" * 80)
            print("AI RESPONSE:")
            print(data.get("response", "<NO RESPONSE FIELD>"))
            print("=" * 80)
            print(f"Model used: {data.get('metadata', {}).get('model')}")
            print(f"Provider: {data.get('metadata', {}).get('provider')}")
            print(f"Duration: {data.get('metadata', {}).get('duration_ms')} ms")
            print(f"Actions executed: {data.get('actions')}")

            if status_code == 200 and data.get("response"):
                print("\n[OK] /api/ai/chat endpoint is working correctly!")
                sys.exit(0)
            else:
                print("\n[!] Unexpected response content.")
                sys.exit(1)

    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - t0
        err_body = e.read().decode("utf-8", errors="replace")
        print(f"[!] HTTP Error {e.code} ({elapsed:.2f}s): {err_body}")
        sys.exit(1)
    except Exception as e:
        elapsed = time.perf_counter() - t0
        print(f"[!] Connection / Request failed ({elapsed:.2f}s): {type(e).__name__}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
