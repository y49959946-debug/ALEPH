from __future__ import annotations

import json
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPT_DIR / f"{name}.txt").read_text(encoding="utf-8")


def to_json(obj) -> str:
    """Pydantic 모델이나 dict를 LLM 입력용 JSON 문자열로."""
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump()
    return json.dumps(obj, ensure_ascii=False, indent=2)
