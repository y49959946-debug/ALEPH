"""근거 검증.

원칙: 잘못된 근거는 자동으로 고치지 않고 제외 + 경고 기록 + 건수 집계.
('AI가 없는 근거를 만든 비율'이 실험 지표이기 때문)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..schemas import (
    AnalyzerOutput,
    FirstImpression,
    JudgeOutput,
    PersonaResult,
    Preprocessed,
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


@dataclass
class ValidationReport:
    invalid_evidence_count: int = 0
    warnings: list[str] = field(default_factory=list)

    def warn(self, where: str, msg: str, invalid: bool = True) -> None:
        if invalid:
            self.invalid_evidence_count += 1
        self.warnings.append(f"[{where}] {msg}")

    def to_dict(self) -> dict:
        return {"invalid_evidence_count": self.invalid_evidence_count, "warnings": self.warnings}


class Validator:
    def __init__(self, pre: Preprocessed, report: ValidationReport | None = None):
        self.sentences = {s.id: s for s in pre.sentences}
        self.paragraph_ids = {p.id for p in pre.paragraphs}
        self.report = report or ValidationReport()

    # -- 공통 ---------------------------------------------------------------
    def _filter_ids(self, ids: list[str], where: str) -> list[str]:
        ok = []
        for sid in ids:
            if sid in self.sentences:
                ok.append(sid)
            else:
                self.report.warn(where, f"존재하지 않는 문장 ID '{sid}' 제외")
        return ok

    # -- Analyzer -----------------------------------------------------------
    def analyzer(self, out: AnalyzerOutput) -> AnalyzerOutput:
        obs, sig = out.observations, out.signals

        obs.paragraph_roles = [
            r for r in obs.paragraph_roles
            if r.paragraph_id in self.paragraph_ids
            or self.report.warn("analyzer.paragraph_roles", f"없는 문단 '{r.paragraph_id}' 제외")
        ]

        mentions = []
        for m in obs.tech_mentions:
            if m.sentence_id not in self.sentences:
                self.report.warn("analyzer.tech_mentions", f"없는 문장 '{m.sentence_id}' 제외")
                continue
            text = _norm(self.sentences[m.sentence_id].text).lower()
            terms = [t for t in m.terms if _norm(t).lower() in text]
            for t in set(m.terms) - set(terms):
                self.report.warn("analyzer.tech_mentions", f"{m.sentence_id}에 없는 기술명 '{t}' 제외")
            if terms:
                m.terms = terms
                mentions.append(m)
        obs.tech_mentions = mentions

        signals, seen = [], set()
        for s in sig.sentence_signals:
            where = f"analyzer.signals.{s.sentence_id}"
            if s.sentence_id not in self.sentences:
                self.report.warn(where, "존재하지 않는 문장 ID — 신호 제외")
                continue
            if s.sentence_id in seen:
                self.report.warn(where, "같은 문장에 중복 신호 — 뒤의 것 제외", invalid=False)
                continue
            if _norm(s.quote) not in _norm(self.sentences[s.sentence_id].text):
                self.report.warn(where, f"인용 '{s.quote}'이(가) 원문에 없음 — 신호 제외")
                continue
            if not 1 <= s.intensity <= 3:
                self.report.warn(where, f"강도 {s.intensity} 범위 밖 → 보정", invalid=False)
                s.intensity = _clamp(s.intensity, 1, 3)
            seen.add(s.sentence_id)
            signals.append(s)
        sig.sentence_signals = signals
        missing = [sid for sid in self.sentences if sid not in seen]
        if missing:
            self.report.warn("analyzer.signals", f"신호가 없는 문장 {len(missing)}개: {', '.join(missing)}",
                             invalid=False)

        scores = []
        for p in sig.paragraph_scores:
            if p.paragraph_id not in self.paragraph_ids:
                self.report.warn("analyzer.paragraph_scores", f"없는 문단 '{p.paragraph_id}' 제외")
                continue
            for k in ("confidence", "passion", "tension", "concreteness"):
                v = getattr(p, k)
                if not 1 <= v <= 5:
                    self.report.warn("analyzer.paragraph_scores", f"{p.paragraph_id}.{k}={v} 범위 밖 → 보정",
                                     invalid=False)
                    setattr(p, k, _clamp(v, 1, 5))
            scores.append(p)
        sig.paragraph_scores = scores
        return out

    # -- 첫인상 -------------------------------------------------------------
    def impression(self, imp: FirstImpression) -> FirstImpression:
        imp.evidence_sentence_ids = self._filter_ids(imp.evidence_sentence_ids, "impression")
        return imp

    # -- 페르소나 -----------------------------------------------------------
    def persona(self, res: PersonaResult, criteria: list[str]) -> PersonaResult:
        where = f"persona.{res.persona_id}"
        for group in ("strengths", "weaknesses"):
            kept = []
            for pt in getattr(res, group):
                pt.evidence_ids = self._filter_ids(pt.evidence_ids, f"{where}.{group}")
                if pt.evidence_ids:
                    kept.append(pt)
                else:
                    self.report.warn(f"{where}.{group}", f"유효한 근거가 없는 지적 제외: {pt.claim[:30]}")
            setattr(res, group, kept)

        recs = []
        for r in res.recommendations:
            r.target_ids = self._filter_ids(r.target_ids, f"{where}.recommendations")
            if r.target_ids:
                recs.append(r)
            else:
                self.report.warn(f"{where}.recommendations", f"대상 문장이 없는 제안 제외: {r.suggestion[:30]}")
        res.recommendations = recs

        for s in res.scores:
            if not 1 <= s.score <= 5:
                self.report.warn(where, f"점수 {s.criterion}={s.score} 범위 밖 → 보정", invalid=False)
                s.score = _clamp(s.score, 1, 5)
        unknown = [s.criterion for s in res.scores if s.criterion not in criteria]
        if unknown:
            self.report.warn(where, f"정의되지 않은 평가 기준: {unknown}", invalid=False)
        return res

    # -- Judge --------------------------------------------------------------
    def judge(self, out: JudgeOutput, persona_ids: list[str]) -> JudgeOutput:
        for issue in out.key_issues:
            bad = [p for p in issue.raised_by if p not in persona_ids]
            for p in bad:
                self.report.warn("judge", f"존재하지 않는 페르소나 '{p}' 제외")
            issue.raised_by = [p for p in issue.raised_by if p in persona_ids]
            issue.evidence_ids = self._filter_ids(issue.evidence_ids, "judge.key_issues")
        return out
