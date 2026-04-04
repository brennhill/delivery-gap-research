#!/usr/bin/env python3
"""Shared LLM dispatch utilities for scoring scripts.

Extracts common API/CLI calling and response parsing logic
used by both score-specs.py and score-formality.py.
"""

import json
import re


def has_api_key() -> bool:
    """Check if ANTHROPIC_API_KEY is set."""
    import os
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def score_via_api(prompt: str, model: str, max_tokens: int = 1024) -> str:
    """Call Anthropic API directly. Fast, cheap, uses API credits not subscription."""
    import anthropic
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def score_via_cli(prompt: str, model: str) -> str:
    """Fall back to claude CLI. Uses subscription quota."""
    import subprocess
    result = subprocess.run(
        ["claude", "--model", model, "-p", prompt, "--output-format", "text", "--max-turns", "1"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"CLI error: {result.stderr[:200]}")
    return result.stdout.strip()


def parse_llm_response(text: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"error": f"Parse error: {text[:200]}"}
