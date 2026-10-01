"""단일 AI 비교 기준.

- Single-A (주 비교): 세 평가자의 기준을 모두(중복 제외) 한 번에 준다. 입력은 Multi와 같다.
- Single-B (보조): "이 자기소개서를 평가하고 개선점을 알려줘" 수준의 단순 프롬프트.
  채점을 위해 출력 형식(근거 문장 ID)만 같게 맞춘다.
"""
from __future__ import annotations

from ..preprocess import numbered_text
from ..schemas import Observations, PersonaLLMOutput, PersonaResult, Preprocessed
from ..utils.llm import LLMClient
from . import load_prompt, to_json
from .persona import Persona

TEMPERATURE = 0.4


def all_criteria(personas: list[Persona]) -> list[str]:
    out: list[str] = []
    for p in personas:
        out += [c for c in p.criteria if c not in out]
    return out


def run_a(client: LLMClient, personas: list[Persona], pre: Preprocessed, observations: Observations) -> PersonaResult:
    crit = "\n".join(f"- {c}" for c in all_criteria(personas))
    user = "## 자기소개서 원문\n" + numbered_text(pre, with_facts=True) + "\n\n## 분석기가 관찰한 사실\n" + to_json(observations)
    raw = client.generate(system=load_prompt("single").format(criteria=crit), user=user,
                          schema=PersonaLLMOutput, temperature=TEMPERATURE)
    return PersonaResult(persona_id="single_a", status="single", **raw.model_dump())


def run_b(client: LLMClient, pre: Preprocessed) -> PersonaResult:
    user = "## 자기소개서\n" + numbered_text(pre)
    raw = client.generate(system=load_prompt("single_simple"), user=user,
                          schema=PersonaLLMOutput, temperature=TEMPERATURE)
    return PersonaResult(persona_id="single_b", status="single", **raw.model_dump())
