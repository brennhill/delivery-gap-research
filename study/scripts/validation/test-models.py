#!/usr/bin/env python3
import anthropic

c = anthropic.Anthropic()

# List all available models
try:
    models = c.models.list()
    print("Available models:")
    for m in models.data:
        print(f"  {m.id}")
except Exception:
    # Fallback: brute force test common IDs
    print("models.list() not available, testing known IDs:")
    candidates = [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5-20251022",
        "claude-sonnet-4-6-20260312",
        "claude-opus-4-20250514",
        "claude-opus-4-6-20260326",
        "claude-3-5-haiku-20241022",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-latest",
        "claude-3-haiku-20240307",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
    ]
    for m in candidates:
        try:
            c.messages.create(model=m, max_tokens=5, messages=[{"role": "user", "content": "hi"}])
            print(f"  OK: {m}")
        except Exception as e:
            err = str(e)
            if "not_found" in err:
                print(f"  404: {m}")
            elif "authentication" in err:
                print(f"  AUTH: {m}")
            else:
                print(f"  FAIL: {m} ({err[:50]})")
