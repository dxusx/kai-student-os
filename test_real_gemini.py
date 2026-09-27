"""
test_real_gemini.py — Direct Google Gemini 3.5 Flash live test without mocks or fallbacks.
Tests real connectivity and response through the configured GEMINI_BASE_URL proxy or direct API.
"""

import os
import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add repo root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import settings

def main():
    print("=" * 80)
    print("      REAL GOOGLE GEMINI 3.5 FLASH VERIFICATION (NO MOCKS / NO FALLBACKS)")
    print("=" * 80)

    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    base_url = settings.gemini_base_url or os.getenv("GEMINI_BASE_URL")
    model_name = settings.gemini_model or os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"

    # Mask API key for security
    masked_key = f"{api_key[:6]}...{api_key[-4:]}" if api_key and len(api_key) > 10 else ("None" if not api_key else "***")

    print(f"[*] API Key present:  {bool(api_key)} ({masked_key})")
    print(f"[*] Base URL Proxy:   {base_url or 'Direct (generativelanguage.googleapis.com)'}")
    print(f"[*] Target Model:     {model_name}")
    print("-" * 80)

    if not api_key:
        print("[!] ERROR: GEMINI_API_KEY is not set in .env. Exiting.")
        sys.exit(1)

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        print(f"[!] ERROR: google-genai SDK is not installed: {e}")
        sys.exit(1)

    print("[*] Initializing genai.Client...")
    http_opts = types.HttpOptions(base_url=base_url) if base_url else None
    client = genai.Client(api_key=api_key, http_options=http_opts)
    print("[+] Client initialized successfully.")

    prompt = "Назови 3 главных предмета студента радиотехнического факультета КАИ в одно предложение."
    print(f"\n[*] Sending live request to Gemini API:")
    print(f'    Model:   "{model_name}"')
    print(f'    Prompt:  "{prompt}"')
    print("    Waiting for real model response...")

    t0 = time.perf_counter()
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                thinking_config=types.ThinkingConfig(thinking_budget=1024),
            ),
        )
        duration_ms = int((time.perf_counter() - t0) * 1000)

        if not resp.text or not resp.text.strip():
            print(f"\n[!] ERROR: Empty response returned by model ({duration_ms} ms)")
            sys.exit(1)

        print(f"\n[+] SUCCESS! Response received in {duration_ms} ms:")
        print("=" * 80)
        print(resp.text.strip())
        print("=" * 80)
        print("[OK] Real Gemini 3.5 Flash responded successfully without fallbacks!")
        sys.exit(0)

    except Exception as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        print(f"\n[!] GEMINI API CALL FAILED after {duration_ms} ms:")
        print(f"    Exception Type: {type(e).__name__}")
        print(f"    Exception Str:  {e}")
        
        status_code = getattr(e, "status_code", getattr(e, "code", None))
        if status_code:
            print(f"    HTTP Status:    {status_code}")
        
        import traceback
        print("\nFull Traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
