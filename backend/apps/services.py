import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"billing", "technical", "account", "general"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}

SYSTEM_PROMPT = """You are a support ticket classifier for a software company.
Given a support ticket description, classify it into a category and assign a priority level.

Categories:
- billing: payment issues, invoices, subscriptions, refunds, pricing
- technical: bugs, errors, crashes, integrations, performance, API issues
- account: login, password, access, permissions, profile settings
- general: feature requests, general questions, feedback, other

Priority levels:
- critical: system down, data loss, security breach, complete service outage
- high: major feature broken, significant business impact, many users affected
- medium: partial functionality affected, workaround available, moderate impact
- low: minor inconvenience, cosmetic issue, general question, feature request

Respond ONLY with valid JSON in this exact format (no other text):
{"category": "<category>", "priority": "<priority>"}"""

FEW_SHOT_EXAMPLES = [
    {
        "description": "I can't log into my account. My password reset email never arrives.",
        "output": '{"category": "account", "priority": "high"}',
    },
    {
        "description": "The API is returning 500 errors for all requests, our entire app is down.",
        "output": '{"category": "technical", "priority": "critical"}',
    },
    {
        "description": "I was charged twice for my subscription this month.",
        "output": '{"category": "billing", "priority": "high"}',
    },
    {
        "description": "Can you add dark mode to the dashboard?",
        "output": '{"category": "general", "priority": "low"}',
    },
]


def _build_prompt(description: str) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for ex in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": ex["description"]})
        messages.append({"role": "assistant", "content": ex["output"]})
    messages.append({"role": "user", "content": description})

    prompt = "<s>"
    for i, msg in enumerate(messages):
        if msg["role"] == "system":
            prompt += f"[INST] {msg['content']}\n\n"
        elif msg["role"] == "user":
            if i == 0:
                prompt += f"{msg['content']} [/INST]"
            else:
                prompt += f"[INST] {msg['content']} [/INST]"
        elif msg["role"] == "assistant":
            prompt += f" {msg['content']} </s><s>"
    return prompt


def _parse_llm_response(text: str) -> dict | None:
    match = re.search(r'\{[^}]+\}', text, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group())
        category = data.get("category", "").lower().strip()
        priority = data.get("priority", "").lower().strip()

        if category in VALID_CATEGORIES and priority in VALID_PRIORITIES:
            return {"suggested_category": category, "suggested_priority": priority}
    except (json.JSONDecodeError, AttributeError):
        pass

    return None


def classify_ticket(description: str) -> dict:
    api_key = settings.HUGGINGFACE_API_KEY
    model = settings.HUGGINGFACE_MODEL

    if not api_key:
        logger.warning("HUGGINGFACE_API_KEY not set — returning defaults")
        return {"suggested_category": "general", "suggested_priority": "medium"}

    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": _build_prompt(description),
        "parameters": {
            "max_new_tokens": 60,
            "temperature": 0.1,
            "return_full_text": False,
            "stop": ["</s>", "\n\n"],
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and data:
            generated = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            generated = data.get("generated_text", "")
        else:
            generated = ""

        result = _parse_llm_response(generated)
        if result:
            logger.info(f"LLM classified ticket: {result}")
            return result

        logger.warning(f"LLM returned unparseable response: {generated[:200]}")

    except requests.exceptions.Timeout:
        logger.error("HuggingFace API request timed out")
    except requests.exceptions.HTTPError as e:
        logger.error(f"HuggingFace API HTTP error: {e.response.status_code} — {e.response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.error(f"HuggingFace API request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in classify_ticket: {e}")

    return {"suggested_category": "general", "suggested_priority": "medium"}
