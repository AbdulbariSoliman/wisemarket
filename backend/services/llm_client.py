import logging
import os
import time
from typing import List

import litellm
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
litellm.suppress_debug_info = True

INTENT_MODEL   = os.environ.get("LLM_INTENT_MODEL",   "groq/llama-3.1-8b-instant")
REFINER_MODEL  = os.environ.get("LLM_REFINER_MODEL",  "groq/llama-3.3-70b-versatile")
FALLBACK_MODEL = os.environ.get("LLM_FALLBACK_MODEL", "groq/llama-3.1-8b-instant")


def _call(model, messages, max_tokens=500, temperature=0.3):
    response = litellm.completion(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


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
