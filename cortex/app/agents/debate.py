"""V1 토론 (Round 1).

평가자마다 다른 두 평가자의 첫 평가(Round 0)를 익명(평가자 A·B) + 평가 기준 목록으로 보고,
동의·반대를 밝힌 뒤 자기 평가를 유지하거나 고친다. 세 명은 서로의 Round 1을 보지 않는다 (동시 응답).
"""
from __future__ import annotations

from ..preprocess import numbered_text
from ..schemas import DebateLLMOutput, DebateResult, PersonaResult, Preprocessed
from ..utils.llm import LLMClient
from . import load_prompt, to_json
from .persona import Persona

ALIASES = ["A", "B", "C", "D"]


def aliases_for(me: str, persona_ids: list[str]) -> dict[str, str]:
    """{이름표: persona_id}. 다른 평가자를 원래 순서대로 A, B …로 부른다. (run.json에 기록)"""
    others = [p for p in persona_ids if p != me]
    return {ALIASES[i]: pid for i, pid in enumerate(others)}


def _strip(r: PersonaResult) -> dict:
    d = r.model_dump()
    d.pop("persona_id", None)
    d.pop("status", None)
    return d


def run(client: LLMClient, persona: Persona, pre: Preprocessed, own: PersonaResult,
        others: dict[str, tuple[list[str], PersonaResult]]) -> DebateResult:
    """others: {이름표: (평가 기준 목록, 그 평가자의 Round 0 결과)}"""
    criteria = "\n".join(f"- {c}" for c in persona.criteria)
    system = load_prompt("debate").format(name=persona.name, role=persona.role, criteria=criteria)
    parts = ["## 자기소개서 원문", numbered_text(pre), "", "## 네 첫 평가", to_json(_strip(own))]
    for alias, (crit, res) in others.items():
        parts += ["", f"## 평가자 {alias}의 첫 평가", "보는 기준: " + ", ".join(crit), to_json(_strip(res))]
    raw = client.generate(system=system, user="\n".join(parts), schema=DebateLLMOutput,
                          temperature=persona.temperature)
    return DebateResult(persona_id=persona.id, **raw.model_dump())
