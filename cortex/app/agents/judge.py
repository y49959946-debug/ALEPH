"""Judge: 페르소나 의견만 종합한다. 새 문제를 만들지 않는다."""
from __future__ import annotations

from ..preprocess import numbered_text
from ..schemas import JudgeOutput, PersonaResult, Preprocessed
from ..utils.llm import LLMClient
from . import load_prompt, to_json

TEMPERATURE = 0.2


def run(client: LLMClient, pre: Preprocessed, results: list, extra: str = "") -> JudgeOutput:
    parts = ["## 자기소개서 원문", numbered_text(pre), "", "## 평가자별 결과"]
    for r in results:
        parts.append(f"\n### persona_id: {r.persona_id}")
        parts.append(to_json(r))
    if extra:
        parts += ["", extra]
    return client.generate(
        system=load_prompt("judge"),
        user="\n".join(parts),
        schema=JudgeOutput,
        temperature=TEMPERATURE,
    )
