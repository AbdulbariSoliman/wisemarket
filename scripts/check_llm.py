"""
Check that the chat's AI models answer, using your GROQ_API_KEY.

    python scripts/check_llm.py

Prints which model answered and how long it took. If a model fails, the
message usually says why (wrong key, model shut down, rate limit).
"""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services import llm_client as llm  # noqa: E402

if not os.environ.get("GROQ_API_KEY"):
    sys.exit("GROQ_API_KEY is not set")

for label, model in (("intent", llm.INTENT_MODEL), ("answers", llm.REFINER_MODEL)):
    start = time.perf_counter()
    try:
        reply = llm._call(model, llm.build_messages("Answer in one short sentence.",
                                                    "Name one Swiss supermarket."), max_tokens=40)
        print(f"OK    {label:8} {model:28} {time.perf_counter() - start:5.1f}s  {reply[:60]!r}")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL  {label:8} {model:28} {type(e).__name__}: {str(e)[:150]}")
