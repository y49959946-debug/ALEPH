"""Analyzer: 관찰 사실(observations)과 인상 신호(signals)를 한 번의 호출로 만든다."""
from __future__ import annotations

from ..preprocess import numbered_text
from ..schemas import AnalyzerOutput, Preprocessed
from ..utils.llm import LLMClient
from . import load_prompt

TEMPERATURE = 0.0  # 일관성을 위해 최저값


def run(client: LLMClient, pre: Preprocessed) -> AnalyzerOutput:
    user = "다음 자기소개서를 분석하라.\n\n" + numbered_text(pre, with_facts=True)
    return client.generate(
        system=load_prompt("analyzer"),
        user=user,
        schema=AnalyzerOutput,
        temperature=TEMPERATURE,
    )
