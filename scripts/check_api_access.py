"""Check API access for every model the study calls (not a pipeline step).

One minimal call per provider confirms that the key in .env works and that
the model ID is right, and records the model / version string the API
returns. Keys are read from .env and never printed or saved.

Writes results/api_access_check.json.

Usage:
    python scripts/check_api_access.py
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "results" / "api_access_check.json"
PROMPT = "Reply with the single word OK."


def check_openai():
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    r = client.responses.create(model="gpt-5.6-luna", input=PROMPT)
    return {"model_requested": "gpt-5.6-luna", "model_returned": r.model, "text": r.output_text}


def check_anthropic():
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    r = client.messages.create(model="claude-sonnet-5-5", max_tokens=1024,
                               messages=[{"role": "user", "content": PROMPT}])
    text = "".join(b.text for b in r.content if b.type == "text")
    return {"model_requested": "claude-sonnet-5-5", "model_returned": r.model,
            "stop_reason": r.stop_reason, "text": text}


def check_google():
    from google import genai
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    r = client.models.generate_content(model="gemini-3.5-flash-lite", contents=PROMPT)
    return {"model_requested": "gemini-3.5-flash-lite", "model_returned": r.model_version,
            "text": r.text}


def check_deepseek():
    r = requests.post("https://api.deepseek.com/chat/completions", timeout=120,
                      headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"},
                      json={"model": "deepseek-v4-pro", "thinking": {"type": "disabled"},
                            "messages": [{"role": "user", "content": PROMPT}]})
    r.raise_for_status()
    j = r.json()
    return {"model_requested": "deepseek-v4-pro", "model_returned": j.get("model"),
            "system_fingerprint": j.get("system_fingerprint"),
            "text": j["choices"][0]["message"]["content"]}


def main():
    load_dotenv(ROOT / ".env")
    results = {}
    for name, check in [("openai", check_openai), ("anthropic", check_anthropic),
                        ("google", check_google), ("deepseek", check_deepseek)]:
        try:
            results[name] = {"ok": True, **check()}
        except Exception as e:   # report the error type and message, never the key
            results[name] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"}
        print(name, json.dumps(results[name]))
    OUT_PATH.write_text(json.dumps({
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results": results}, indent=1) + "\n")
    print(f"Saved {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
