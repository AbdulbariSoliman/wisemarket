import logging
import os
import time
from typing import List

import litellm
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
litellm.suppress_debug_info = True

# Groq shut down llama-3.1-8b-instant and llama-3.3-70b-versatile on 16 Aug 2026;
# these are its recommended replacements. Override with the env vars if Groq
# changes its line-up again.
INTENT_MODEL   = os.environ.get("LLM_INTENT_MODEL",   "groq/openai/gpt-oss-20b")
REFINER_MODEL  = os.environ.get("LLM_REFINER_MODEL",  "groq/openai/gpt-oss-120b")
FALLBACK_MODEL = os.environ.get("LLM_FALLBACK_MODEL", "groq/openai/gpt-oss-20b")

# Reasoning models think before they answer, and that thinking counts towards
# max_tokens. Keep it short and leave room for it, or the answer comes back empty.
REASONING_HEADROOM = 1024


def _is_reasoning_model(model: str) -> bool:
    return "gpt-oss" in model or "qwen3" in model


def _call(model, messages, max_tokens=500, temperature=0.3):
    kwargs = {}
    if _is_reasoning_model(model):
        max_tokens += REASONING_HEADROOM
        kwargs["extra_body"] = {"reasoning_effort": "low"}
    response = litellm.completion(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        **kwargs,
    )
    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise RuntimeError(f"{model} returned an empty answer")
    return content


def call_intent(messages, max_tokens=200):
    start = time.perf_counter()
    try:
        result = _call(INTENT_MODEL, messages, max_tokens, temperature=0.1)
        logger.info("Intent %.0fms", (time.perf_counter() - start) * 1000)
        return result
    except Exception as e:
        logger.warning("Intent failed (%s), fallback", e)
        return _call(FALLBACK_MODEL, messages, max_tokens, temperature=0.1)


def call_refiner(messages, max_tokens=600):
    start = time.perf_counter()
    try:
        result = _call(REFINER_MODEL, messages, max_tokens, temperature=0.4)
        logger.info("Refiner %.0fms", (time.perf_counter() - start) * 1000)
        return result
    except Exception as e:
        logger.warning("Refiner failed (%s), fallback", e)
        return _call(INTENT_MODEL, messages, max_tokens, temperature=0.4)


def build_messages(system, user):
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]


def build_messages_with_history(system, history, user):
    trimmed = history[-6:] if len(history) > 6 else history
    return [
        {"role": "system", "content": system},
        *trimmed,
        {"role": "user",   "content": user},
    ]
