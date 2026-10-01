"""Shift Log: 토론 전(Round 0)과 후(Round 1)를 코드가 비교한다. (AI 호출 없음)

분류
- maintained: 점수·강점·약점 문장이 그대로
- changed_with_valid_evidence: 바뀌었고, 스스로 밝힌 변경(changes)에 원문에 실제로 있는 문장 ID와 이유가 있음
  (코드가 확인하는 것은 '근거 문장이 존재한다'까지. 그 근거가 변경을 정말 뒷받침하는지는 사람이 일부 확인)
- changed_without_evidence: 바뀌었는데 근거가 없거나 원문에 없는 문장 ID → 동조 의심

추가 기록
- adopted_from: 새로 생긴 약점·강점 문장이 다른 평가자의 Round 0에 있던 것이면 누구의 것이었는지
- self_report_mismatch: 실제 변화와 스스로 밝힌 변경이 맞지 않음 (바뀌었는데 changes가 비었거나, 그 반대)
- 점수 변화와 지적 변화는 따로 기록한다
"""
from __future__ import annotations


def _ids(points: list[dict]) -> set[str]:
    return {i for p in points for i in (p.get("evidence_ids") or [])}


def compute(round0: list[dict], round1: list[dict], sentence_ids: set[str], aliases: dict[str, dict[str, str]]) -> list[dict]:
    r0 = {r["persona_id"]: r for r in round0}
    out = []
    for r in round1:
        pid = r["persona_id"]
        before = r0.get(pid)
        if not before:
            continue
        s0 = {s["criterion"]: s["score"] for s in before.get("scores", [])}
        s1 = {s["criterion"]: s["score"] for s in r.get("scores", [])}
        score_changes = {c: [s0.get(c), s1.get(c)] for c in sorted(set(s0) | set(s1)) if s0.get(c) != s1.get(c)}
        w0, w1 = _ids(before.get("weaknesses", [])), _ids(r.get("weaknesses", []))
        g0, g1 = _ids(before.get("strengths", [])), _ids(r.get("strengths", []))
        added_w, removed_w = sorted(w1 - w0), sorted(w0 - w1)
        added_s, removed_s = sorted(g1 - g0), sorted(g0 - g1)
        changed_scores = bool(score_changes)
        changed_points = bool(added_w or removed_w or added_s or removed_s)
        changed = changed_scores or changed_points

        changes = r.get("changes") or []
        valid = [c for c in changes if (c.get("reason") or "").strip() and any(i in sentence_ids for i in (c.get("evidence_ids") or []))]
        if not changed:
            kind = "maintained"
        elif valid:
            kind = "changed_with_valid_evidence"
        else:
            kind = "changed_without_evidence"

        # 새로 생긴 지적이 다른 평가자의 첫 평가에 있던 문장이면 기록 (동조 흐름 추적)
        adopted: dict[str, list[str]] = {}
        for sid in added_w:
            src = [o for o, rr in r0.items() if o != pid and sid in _ids(rr.get("weaknesses", []))]
            if src:
                adopted[f"weakness:{sid}"] = src
        for sid in added_s:
            src = [o for o, rr in r0.items() if o != pid and sid in _ids(rr.get("strengths", []))]
            if src:
                adopted[f"strength:{sid}"] = src

        stances = [x.get("stance") for x in r.get("responses") or []]
        out.append({
            "persona_id": pid,
            "type": kind,
            "score_changes": score_changes,
            "changed_scores": changed_scores,
            "changed_points": changed_points,
            "added_weakness_ids": added_w, "removed_weakness_ids": removed_w,
            "added_strength_ids": added_s, "removed_strength_ids": removed_s,
            "adopted_from": adopted,
            "self_reported_changes": len(changes),
            "valid_reported_changes": len(valid),
            "self_report_mismatch": changed != bool(changes),
            "responses": {"동의": stances.count("동의"), "부분 동의": stances.count("부분 동의"), "반대": stances.count("반대")},
            "aliases": aliases.get(pid, {}),
        })
    return out


LABEL = {
    "maintained": "유지",
    "changed_with_valid_evidence": "근거 있는 변경",
    "changed_without_evidence": "근거 없는 변경",
}


def summary_text(shift: list[dict], names: dict[str, str]) -> str:
    """의장에게 줄 짧은 요약."""
    lines = []
    for s in shift:
        sc = ", ".join(f"{c} {a}→{b}" for c, (a, b) in s["score_changes"].items()) or "점수 변화 없음"
        lines.append(f"- {names.get(s['persona_id'], s['persona_id'])} ({s['persona_id']}): {LABEL[s['type']]} · {sc}")
    return "\n".join(lines)
