"""페르소나 공통 로직. 페르소나별 차이는 personas.yaml에서만 정의한다.

페르소나는 서로의 결과도, 인상 분석(signals)도 보지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from ..preprocess import numbered_text
from ..schemas import Observations, PersonaLLMOutput, PersonaResult, Preprocessed
from ..utils.llm import LLMClient
from . import load_prompt, to_json

PERSONA_FILE = Path(__file__).resolve().parent.parent / "personas.yaml"


@dataclass
class Persona:
    id: str
    name: str
    role: str
    criteria: list[str]
    temperature: float = 0.4

    def system_prompt(self) -> str:
        criteria = "\n".join(f"- {c}" for c in self.criteria)
        return load_prompt("persona_base").format(name=self.name, role=self.role, criteria=criteria)


def load_personas() -> list[Persona]:
    data = yaml.safe_load(PERSONA_FILE.read_text(encoding="utf-8"))
    return [Persona(**p) for p in data["personas"]]


def run(client: LLMClient, persona: Persona, pre: Preprocessed, observations: Observations) -> PersonaResult:
    user = (
        "## 자기소개서 원문\n" + numbered_text(pre, with_facts=True)
        + "\n\n## 분석기가 관찰한 사실\n" + to_json(observations)
    )
    raw = client.generate(
        system=persona.system_prompt(),
        user=user,
        schema=PersonaLLMOutput,
        temperature=persona.temperature,
    )
    return PersonaResult(persona_id=persona.id, status="initial", **raw.model_dump())
