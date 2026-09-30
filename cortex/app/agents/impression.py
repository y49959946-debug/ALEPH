"""첫인상 카드: 원문을 새로 분석하지 않고 signals를 근거로 만든다 (모순 방지)."""
from __future__ import annotations

from ..preprocess import numbered_text
from ..schemas import FirstImpression, FirstImpressionLLM, Preprocessed, Signals
from ..utils.llm import LLMClient
from . import load_prompt, to_json

TEMPERATURE = 0.3


def run(client: LLMClient, pre: Preprocessed, signals: Signals) -> FirstImpression:
    user = (
        "## 원문\n" + numbered_text(pre)
        + "\n\n## 분석기가 만든 인상 신호\n" + to_json(signals)
    )
    raw = client.generate(
        system=load_prompt("impression"),
        user=user,
        schema=FirstImpressionLLM,
        temperature=TEMPERATURE,
    )
    return FirstImpression(
        archetype=raw.archetype,
        summary=raw.summary,
        key_contrast=raw.key_contrast.strip() or None,  # 대조가 없으면 null
        evidence_sentence_ids=raw.evidence_sentence_ids,
    )
