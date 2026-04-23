from __future__ import annotations
import os
import time
from typing import Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY", "")
ACTOR_MODEL      = os.getenv("ACTOR_MODEL",     "gemini-2.5-flash")
EVALUATOR_MODEL  = os.getenv("EVALUATOR_MODEL", "gemini-2.5-flash")
REFLECTOR_MODEL  = os.getenv("REFLECTOR_MODEL", "gemini-2.5-pro")
DEBUG            = os.getenv("DEBUG", "false").lower() == "true"

_client = genai.Client(api_key=GEMINI_API_KEY)


def _call_gemini(prompt: str, model: str, max_tokens: int = 1024, retries: int = 5) -> Tuple[str, int]:
    """Gọi Gemini API, tự retry khi gặp lỗi 503, trả về (response_text, total_tokens_used)."""
    if DEBUG:
        print(f"[DEBUG] model={model}  prompt[:80]={prompt[:80]!r}")

    for attempt in range(retries):
        try:
            response = _client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                ),
            )

            text = response.text or ""

            # Lấy token thật từ usage_metadata
            usage = response.usage_metadata
            total_tokens = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0)
            if total_tokens == 0:
                total_tokens = max(1, len(text.split()))

            if DEBUG:
                print(f"[DEBUG] tokens={total_tokens}  response[:80]={text[:80]!r}")

            return text, total_tokens

        except Exception as e:
            is_last = attempt == retries - 1
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                wait = 10 * (attempt + 1)  # 10s, 20s, 30s, 40s, 50s
                if not is_last:
                    print(f"  ⚠️  503 overloaded, retry {attempt+1}/{retries} sau {wait}s...")
                    time.sleep(wait)
                    continue
            raise


def call_actor(prompt: str) -> Tuple[str, int]:
    """Actor: dùng model yếu nhất để hay sai → Reflexion mới có việc làm."""
    return _call_gemini(prompt, model=ACTOR_MODEL, max_tokens=300)


def call_evaluator(prompt: str) -> Tuple[str, int]:
    """Evaluator: trả về JSON string, được parse bởi agents.py."""
    return _call_gemini(prompt, model=EVALUATOR_MODEL, max_tokens=150)


def call_reflector(prompt: str) -> Tuple[str, int]:
    """Reflector: dùng model mạnh hơn để phân tích lỗi tốt hơn."""
    return _call_gemini(prompt, model=REFLECTOR_MODEL, max_tokens=300)


def test_connection() -> bool:
    """Kiểm tra API key và kết nối Gemini."""
    print("🔧 Testing Gemini connection...")
    print(f"   Actor    : {ACTOR_MODEL}")
    print(f"   Evaluator: {EVALUATOR_MODEL}")
    print(f"   Reflector: {REFLECTOR_MODEL}")

    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print("❌ GEMINI_API_KEY chưa được set trong file .env")
        return False

    try:
        text, tokens = _call_gemini("Say hi in one word.", model=ACTOR_MODEL, max_tokens=10)
        print(f"✅ Gemini OK! Response: {text.strip()!r}  tokens={tokens}")
        return True
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return False


if __name__ == "__main__":
    if test_connection():
        print("\n🧪 Testing Actor...")
        response, tokens = call_actor("Question: Who wrote The Hobbit?\nAnswer: ")
        print(f"Response: {response}\nTokens: {tokens}\n")

        print("🧪 Testing Evaluator...")
        response, tokens = call_evaluator(
            'Question: Who wrote The Hobbit?\nGold answer: J. R. R. Tolkien\nPredicted answer: Tolkien'
        )
        print(f"Response: {response}\nTokens: {tokens}")
