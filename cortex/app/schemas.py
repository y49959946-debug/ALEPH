"""CORTEX V0 데이터 스키마.

LLM 출력용 스키마는 Gemini 구조화 출력과 호환되도록 단순한 타입만 쓴다.
(dict, 숫자 범위 제약 등은 쓰지 않고 범위 검사는 utils/validate.py에서 코드로 한다.)
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 전처리 (코드가 만든다)
# ---------------------------------------------------------------------------


class Sentence(BaseModel):
    id: str  # s01
    paragraph_id: str  # p01
    text: str
    length: int
    has_number: bool


class Paragraph(BaseModel):
    id: str
    sentence_ids: List[str]


class Preprocessed(BaseModel):
    sentences: List[Sentence]
    paragraphs: List[Paragraph]


# ---------------------------------------------------------------------------
# Analyzer (LLM)
# ---------------------------------------------------------------------------

ParagraphRole = Literal["도입", "경험", "결과", "포부", "기타"]
SignalLabel = Literal["자신감", "망설임", "방어적", "열정", "중립"]


class ParagraphRoleItem(BaseModel):
    paragraph_id: str
    role: ParagraphRole


class TechMention(BaseModel):
    sentence_id: str
    terms: List[str] = Field(description="문장에 실제로 등장한 기술·도구 이름")


class Observations(BaseModel):
    """페르소나에게 전달되는 관찰 사실. 판단을 담지 않는다."""

    paragraph_roles: List[ParagraphRoleItem]
    tech_mentions: List[TechMention]


class SentenceSignal(BaseModel):
    sentence_id: str
    label: SignalLabel
    intensity: int = Field(description="1: 은은함, 2: 명확함, 3: 두드러짐")
    quote: str = Field(description="이 신호로 읽히게 만든 원문 일부 (해당 문장에 그대로 있는 짧은 구절)")
    reason: str = Field(description="왜 그렇게 읽히는지 한 문장")


class ParagraphScore(BaseModel):
    paragraph_id: str
    confidence: int = Field(description="자신감 1(망설임)~5(강한 확신)")
    passion: int = Field(description="열정·몰입 1(건조함)~5(높은 몰입)")
    tension: int = Field(description="긴장감 1(여유)~5(방어적·변명조)")
    concreteness: int = Field(description="구체성 1(추상적)~5(수치·사례 중심)")


class Signals(BaseModel):
    """사용자 화면에만 쓰이는 인상 신호. 페르소나에게 주지 않는다."""

    sentence_signals: List[SentenceSignal]
    paragraph_scores: List[ParagraphScore]


class AnalyzerOutput(BaseModel):
    observations: Observations
    signals: Signals


# ---------------------------------------------------------------------------
# 첫인상 (LLM, signals 기반)
# ---------------------------------------------------------------------------


class FirstImpressionLLM(BaseModel):
    archetype: str = Field(description="이 글에서 읽히는 작성자 한 줄 (서로 다른 특징 2개 결합)")
    summary: str
    key_contrast: str = Field(description="글 안의 어조 대조. 실제 대조가 없으면 빈 문자열")
    evidence_sentence_ids: List[str]


class FirstImpression(BaseModel):
    archetype: str
    summary: str
    key_contrast: Optional[str]
    evidence_sentence_ids: List[str]


# ---------------------------------------------------------------------------
# 페르소나 (LLM)
# ---------------------------------------------------------------------------


class CriterionScore(BaseModel):
    criterion: str
    score: int = Field(description="1~5")


class Point(BaseModel):
    claim: str
    evidence_ids: List[str] = Field(description="근거 문장 ID (예: s03)")


class Recommendation(BaseModel):
    suggestion: str
    reason: str
    target_ids: List[str] = Field(description="수정 대상 문장 ID")


class PersonaLLMOutput(BaseModel):
    summary: str = Field(description="이 관점에서의 한 줄 총평")
    scores: List[CriterionScore]
    strengths: List[Point]
    weaknesses: List[Point]
    recommendations: List[Recommendation]


class PersonaResult(PersonaLLMOutput):
    persona_id: str
    status: str = "initial"  # V1: maintained / changed_with_evidence / changed_without_evidence


# ---------------------------------------------------------------------------
# Judge (LLM)
# ---------------------------------------------------------------------------


class JudgeIssue(BaseModel):
    issue: str
    raised_by: List[str] = Field(description="이 문제를 제기한 persona_id 목록")
    evidence_ids: List[str]
    priority: Literal["높음", "중간", "낮음"]


class PersonaPosition(BaseModel):
    persona_id: str
    position: str


class Disagreement(BaseModel):
    topic: str
    positions: List[PersonaPosition]


class JudgeOutput(BaseModel):
    overall_summary: str
    key_issues: List[JudgeIssue]
    disagreements: List[Disagreement]
    keep: List[str] = Field(description="페르소나들이 강점으로 본 유지할 점")
