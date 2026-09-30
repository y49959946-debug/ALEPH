"""자동 채점 (AI 호출 없음).

실행 결과(run.json)를 정답지(data/inputs/answer_key.json)와 비교해 코드로 셀 수 있는 것만 센다.
- 정답지 적중: 샘플마다 '짚어야 할 점'을 평가자(각각)·평가자 합계·의장이 찾았는가
- C1 근거 유효성, C3 약점마다 수정 제안이 있는가, C5 숫자 없는 결과 문장을 짚었는가, C6 상투어 문장을 짚었는가
- 다양성 지표(평가자 간 지적 겹침, 판정이 갈린 문장 수)는 좋다/나쁘다로 판정하지 않고 기록만 한다

한계: '찾았다'는 판정은 문장 번호와 키워드 일치로만 본다. 지적의 질(정확한가, 도움이 되는가)은 사람이 본다.

사용법 (프로젝트 폴더에서):
    python -m scripts.grade                                   # data/runs의 모든 결과
    python -m scripts.grade data\\runs\\20260930_103907_001.json
"""
from __future__ import annotations

import json
import re
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "data" / "inputs" / "answer_key.json"
OUT_DIR = ROOT / "data" / "grades"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CLICHES = ["열정적", "혁신적", "창의적", "다양한", "최선을 다", "책임감", "성장하는", "인재"]  # O3와 같은 목록
NEG_KINDS = ("weakness", "fix", "issue")


# ---------------------------------------------------------------------------
# 결과에서 '지적' 꺼내기 — Single(V1)도 같은 모양으로 꺼내면 같은 채점을 쓸 수 있다
# ---------------------------------------------------------------------------

def findings(run: dict) -> list[dict]:
    out = []

    def add(source, kind, ids, text):
        out.append({"source": source, "kind": kind, "ids": list(ids or []), "text": text or ""})

    for p in run.get("rounds", {}).get("round_0", []):
        pid = p["persona_id"]
        for x in p.get("strengths", []):
            add(pid, "strength", x.get("evidence_ids"), x.get("claim"))
        for x in p.get("weaknesses", []):
            add(pid, "weakness", x.get("evidence_ids"), x.get("claim"))
        for x in p.get("recommendations", []):
            add(pid, "fix", x.get("target_ids"), f"{x.get('suggestion', '')} {x.get('reason', '')}")
    for i in (run.get("judge") or {}).get("key_issues", []):
        add("judge", "issue", i.get("evidence_ids"), i.get("issue"))
    single = run.get("single")  # V1: 단일 AI 결과를 같은 스키마로 저장할 예정
    if single:
        for x in single.get("strengths", []):
            add("single", "strength", x.get("evidence_ids"), x.get("claim"))
        for x in single.get("weaknesses", []):
            add("single", "weakness", x.get("evidence_ids"), x.get("claim"))
        for x in single.get("recommendations", []):
            add("single", "fix", x.get("target_ids"), f"{x.get('suggestion', '')} {x.get('reason', '')}")
    return out


def sample_name(run: dict) -> str | None:
    m = re.search(r"(sample_\d+)", run.get("document", {}).get("source", ""))
    return m.group(1) if m else None


def hits(item: dict, fs: list[dict]) -> set[str]:
    ids, kws = set(item["ids"]), item.get("keywords") or []
    found = set()
    for f in fs:
        if f["kind"] not in NEG_KINDS or not ids & set(f["ids"]):
            continue
        if kws and not any(k in f["text"] for k in kws):
            continue
        found.add(f["source"])
    return found


# ---------------------------------------------------------------------------
# 채점
# ---------------------------------------------------------------------------

def grade(run: dict, key: dict) -> dict:
    name = sample_name(run)
    fs = findings(run)
    personas = [p["persona_id"] for p in run.get("rounds", {}).get("round_0", [])]
    sources = personas + (["judge"] if run.get("judge") else []) + (["single"] if run.get("single") else [])
    sents = run["preprocess"]["sentences"]
    roles = {r["paragraph_id"]: r["role"] for r in run["analyzer"]["observations"].get("paragraph_roles", [])}
    g: dict = {"run_id": run["run_id"], "sample": name, "model": run["metadata"].get("model")}

    # 정답지 적중
    spec = key["samples"].get(name) if name else None
    if spec:
        items = []
        for it in spec["items"]:
            by = hits(it, fs)
            items.append({"key": it["key"], "label": it["label"], "type": it["type"], "found_by": sorted(by)})
        g["items"] = items

        per_source = {}
        for s in sources:
            per_source[s] = round(sum(1 for i in items if s in i["found_by"]) / len(items), 2) if items else None
        per_source["평가자 합계"] = round(sum(1 for i in items if set(i["found_by"]) & set(personas)) / len(items), 2) if items else None
        g["recall"] = per_source
        g["recall_by_type"] = {t: _recall_type(items, t, personas) for t in ("objective", "subjective", "ai_judgment")}
        strong = set(spec.get("strengths", []))
        cited = {i for f in fs if f["kind"] == "strength" for i in f["ids"]}
        g["strengths_found"] = f"{len(strong & cited)}/{len(strong)}" if strong else None
    else:
        g["items"] = None

    # C1 근거 유효성
    g["C1_invalid_evidence"] = run.get("validation", {}).get("invalid_evidence_count")

    # C3 약점마다 수정 제안 (같은 평가자, 같은 문장)
    c3 = {}
    for pid in personas:
        weak = [f for f in fs if f["source"] == pid and f["kind"] == "weakness"]
        fix_ids = {i for f in fs if f["source"] == pid and f["kind"] == "fix" for i in f["ids"]}
        c3[pid] = f"{sum(1 for w in weak if set(w['ids']) & fix_ids)}/{len(weak)}"
    g["C3_weakness_has_fix"] = c3

    # C5 숫자 없는 결과 문장, C6 상투어 문장
    # 주의: C5는 오탐이 있다. "학교 공식 시스템에 통합되었습니다"처럼 숫자 없이도 좋은 결과 문장이 대상에 들어간다.
    #       그래서 C5는 통과/탈락이 아니라 '대상 중 몇 개를 짚었는가'만 기록하고, 해석은 사람이 한다.
    neg_ids = {i for f in fs if f["kind"] in NEG_KINDS and f["source"] != "single" for i in f["ids"]}
    c5 = [s["id"] for s in sents if roles.get(s["paragraph_id"]) == "결과" and not s["has_number"]]
    c6 = [s["id"] for s in sents if any(w in s["text"] for w in CLICHES)]
    g["C5_numberless_result"] = {"targets": c5, "flagged": sorted(set(c5) & neg_ids)} if c5 else "해당 없음"
    g["C6_cliche"] = {"targets": c6, "flagged": sorted(set(c6) & neg_ids)} if c6 else "해당 없음"

    # 다양성 (기록만)
    wsets = {pid: {i for f in fs if f["source"] == pid and f["kind"] == "weakness" for i in f["ids"]} for pid in personas}
    jac = {}
    for a, b in combinations(personas, 2):
        u = wsets[a] | wsets[b]
        jac[f"{a}-{b}"] = round(len(wsets[a] & wsets[b]) / len(u), 2) if u else None
    g["diversity_weakness_overlap"] = jac
    pos = {pid: {i for f in fs if f["source"] == pid and f["kind"] == "strength" for i in f["ids"]} for pid in personas}
    clash = {i for a in personas for b in personas if a != b for i in pos[a] & wsets[b]}
    g["diversity_clash_sentences"] = sorted(clash)
    return g


def _recall_type(items, t, personas):
    sel = [i for i in items if i["type"] == t]
    if not sel:
        return None
    return f"{sum(1 for i in sel if set(i['found_by']) & set(personas))}/{len(sel)}"


# ---------------------------------------------------------------------------
# 출력
# ---------------------------------------------------------------------------

def show(g: dict) -> None:
    print(f"\n━━ {g['sample'] or '샘플 이름 없음'} · {g['run_id']} · {g['model']}")
    if g.get("items"):
        for i in g["items"]:
            mark = "✓" if i["found_by"] else "✗"
            print(f"  {mark} [{i['type'][:4]}] {i['key']}. {i['label']:<24} {', '.join(i['found_by']) or '-'}")
        print(f"  적중률  {', '.join(f'{k} {v}' for k, v in g['recall'].items())}")
        print(f"  유형별  {', '.join(f'{k} {v}' for k, v in g['recall_by_type'].items() if v)}"
              + (f" · 강점 인용 {g['strengths_found']}" if g.get("strengths_found") else ""))
    else:
        print("  (정답지에 없는 샘플 — 적중률 생략)")
    print(f"  C1 원문에 없는 근거 {g['C1_invalid_evidence']}건 · C3 약점→수정제안 {g['C3_weakness_has_fix']}")
    print(f"  C5 숫자 없는 결과 문장 {g['C5_numberless_result']} · C6 상투어 문장 {g['C6_cliche']}")
    print(f"  다양성(기록만) 약점 겹침 {g['diversity_weakness_overlap']} · 판정 갈린 문장 {g['diversity_clash_sentences'] or '-'}")


def main() -> int:
    key = json.loads(KEY_FILE.read_text(encoding="utf-8"))
    files = [Path(a) for a in sys.argv[1:]] or sorted(p for p in (ROOT / "data" / "runs").glob("*.json") if not p.name.startswith("consistency_"))
    if not files:
        print("채점할 결과 파일이 없습니다.")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for f in files:
        g = grade(json.loads(f.read_text(encoding="utf-8")), key)
        show(g)
        (OUT_DIR / f"{g['run_id']}.json").write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n채점 결과 저장: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
