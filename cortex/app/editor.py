"""편집자: 평가 결과를 화면용 짧은 글로 옮긴다. (AI 호출 1번)

평가 결과(rounds, judge 등)는 건드리지 않고 run["display"]에만 저장한다.
그래서 자동 채점과 실험 비교에는 영향이 없다. 화면(app/web.py)은 display가 있으면 짧은 글을,
없거나 검증에 실패한 항목은 원래 평가 글을 보여준다.

검증 (코드)
- ref가 입력 항목과 1:1로 맞는지 (없는 항목은 원문으로, 모르는 ref는 버림)
- 글자 수 (headline 32자, detail 70자 초과 시 원문으로)
- 핵심어: 원래 글의 영문 기술 이름(Redis 등)이 모두 빠지면 원문으로, 숫자만 빠지면 경고
- 말투: "~니다"로 끝나면 경고 (해요체 규칙 위반)

사용법 (프로젝트 폴더에서):
    python -m app.editor                     # 샘플마다 최신 결과(사이트에 쓰이는 것) 중 display가 없는 것
    python -m app.editor data\\runs\\ID.json   # 특정 결과
    python -m app.editor --force             # 이미 있어도 다시
    python -m app.editor --mock              # AI 없이 시험
평가와 다른 모델(예: 로컬 Ollama)을 써도 된다. 화면용 글이라 실험 결과에는 영향이 없다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from .agents import load_prompt
from .schemas import DisplayLine, EditorOutput
from .utils.llm import LLMClient, LLMError, make_client

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "data" / "runs"
TEMPERATURE = 0.2
MAX_HEAD, MAX_DETAIL = 32, 70
# 토론 대사는 말하듯 쓰므로 조금 더 길어도 된다
LIMITS = {"reply": (48, 80), "change": (48, 80), "kept": (48, 80)}  # *_sum은 기본 길이(32, 70)
_KEY = re.compile(r"\d[\d,.]*|[A-Za-z][A-Za-z+#.]{1,}")


def sources(run: dict) -> list[dict]:
    """화면에 나오는 평가 글 목록. ref 규칙은 화면(app.html)과 같다."""
    out = []

    def add(ref, kind, text, ctx=""):
        if text:
            out.append({"ref": ref, "kind": kind, "text": text, **({"context": ctx} if ctx else {})})

    imp = run.get("impression", {})
    add("impression.title", "title", imp.get("archetype"))
    add("impression.summary", "summary", imp.get("summary"))
    for p in run.get("rounds", {}).get("round_0", []):
        pid = p["persona_id"]
        add(f"{pid}.summary", "summary", p.get("summary"))
        for i, x in enumerate(p.get("strengths", [])):
            add(f"{pid}.s{i}", "strength", x.get("claim"))
        for i, x in enumerate(p.get("weaknesses", [])):
            add(f"{pid}.w{i}", "weakness", x.get("claim"))
        for i, x in enumerate(p.get("recommendations", [])):
            add(f"{pid}.r{i}", "fix", x.get("suggestion"), x.get("reason", ""))
    j = run.get("judge") or {}
    add("judge.summary", "summary", j.get("overall_summary"))
    for i, x in enumerate(j.get("key_issues", [])):
        add(f"judge.i{i}", "issue", x.get("issue"))
    for i, k in enumerate(j.get("keep", [])):
        add(f"judge.k{i}", "keep", k)
    # 토론 (V1): 서로에게 말하듯 옮긴다. 토론 중에는 이름이 A·B로 가려졌으므로, 화면용 글에서는 실제 역할 이름으로 부른다
    names = {"recruiter": "채용 담당자", "technical": "기술 전문가", "reader": "비개발 직군 면접관"}
    aliases = run.get("round_1_aliases", {})
    for p in run.get("rounds", {}).get("round_1", []):
        pid = p["persona_id"]
        al = {a: names.get(o, o) for a, o in aliases.get(pid, {}).items()}
        who = names.get(pid, pid)
        for i, x in enumerate(p.get("responses", [])):
            to = al.get(x.get("to"), x.get("to"))
            ctx = f"말하는 사람: {who} / 듣는 사람: {to} / 입장: {x.get('stance')} / 무엇에 대해: {x.get('about')}"
            add(f"debate.{pid}.r{i}", "reply", x.get("reason"), ctx)          # 토론 장면용: 말하듯
            add(f"debate.{pid}.r{i}.sum", "reply_sum", x.get("reason"), ctx)  # 결과 화면용: 담백한 요약
        for i, c in enumerate(p.get("changes", [])):
            ctx = f"말하는 사람: {who} / 이름표: {json.dumps(al, ensure_ascii=False)}"
            add(f"debate.{pid}.c{i}", "change", f"{c.get('what')}. {c.get('reason')}", ctx)
            add(f"debate.{pid}.c{i}.sum", "change_sum", c.get("reason"), ctx)
        ctx = f"말하는 사람: {who} / 이름표: {json.dumps(al, ensure_ascii=False)}"
        add(f"debate.{pid}.k", "kept", p.get("kept_reason"), ctx)
        add(f"debate.{pid}.k.sum", "kept_sum", p.get("kept_reason"), ctx)
    return out


def _keywords(text: str) -> set[str]:
    return {k.strip(".,") for k in _KEY.findall(text or "") if len(k.strip(".,")) >= 2 or k[0].isdigit()}


def validate(src: list[dict], out: EditorOutput) -> dict:
    by_ref = {s["ref"]: s for s in src}
    lines, fallback, warnings = {}, [], []
    for ln in out.lines:
        if ln.ref not in by_ref or ln.ref in lines:
            continue
        head, detail = ln.headline.strip(), (ln.detail or "").strip()
        mh, md = LIMITS.get(by_ref[ln.ref]["kind"], (MAX_HEAD, MAX_DETAIL))
        if not head or len(head) > mh or len(detail) > md:
            fallback.append(ln.ref)
            warnings.append({"ref": ln.ref, "type": "length"})
            continue
        src_item = by_ref[ln.ref]
        keys = _keywords(src_item["text"])
        # 괄호 안 예시(예: RDB, 커넥션 풀)는 빠져도 된다. 판단(강점·아쉬움·이슈)에서 기술 이름이 사라질 때만 원문으로
        names = {k for k in _keywords(re.sub(r"\([^)]*\)", "", src_item["text"])) if not k[0].isdigit()}
        both = head + " " + detail
        if names and src_item["kind"] in ("strength", "weakness", "issue") and not any(k in both for k in names):
            # 기술 이름(Redis 등)이 사라지면 "기술 설명이 부족해요"처럼 뭉뚱그려진 것 → 원문으로
            fallback.append(ln.ref)
            warnings.append({"ref": ln.ref, "type": "name_missing", "keywords": sorted(names)})
            continue
        if keys and not any(k in both for k in keys):
            warnings.append({"ref": ln.ref, "type": "keyword_missing", "keywords": sorted(keys)})
        if re.search(r"(니다|함|음)[.!]?$", head):
            warnings.append({"ref": ln.ref, "type": "tone"})
        lines[ln.ref] = {"headline": head, "detail": detail}
    for r in by_ref:
        if r not in lines and r not in fallback:
            fallback.append(r)
            warnings.append({"ref": r, "type": "missing"})
    return {"lines": lines, "fallback": fallback, "warnings": warnings}


def _mock(src: list[dict]) -> EditorOutput:
    return EditorOutput(lines=[DisplayLine(ref=s["ref"], headline=s["text"][:18] + "…", detail="") for s in src])


def run_editor(run: dict, client: LLMClient) -> dict:
    src = sources(run)
    if client.model_name == "mock":
        out = _mock(src)
    else:
        text = "\n".join(f"[{s['id']}] {s['text']}" for s in run["preprocess"]["sentences"])
        user = "## 자기소개서 원문 (참고용)\n" + text + "\n\n## 옮길 항목\n" + json.dumps(src, ensure_ascii=False, indent=2)
        out = client.generate(system=load_prompt("editor"), user=user, schema=EditorOutput, temperature=TEMPERATURE)
    res = validate(src, out)
    prompt = (Path(__file__).resolve().parent / "prompts" / "editor.txt").read_bytes()
    return {
        **res,
        "model": client.model_name,
        "prompt_hash": hashlib.sha256(prompt).hexdigest()[:12],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


def apply(path: Path, client: LLMClient, force: bool = False, log=print) -> bool:
    run = json.loads(path.read_text(encoding="utf-8"))
    if client.model_name == "mock" and run.get("metadata", {}).get("model") != "mock":
        log(f"  건너뜀 (가짜 응답은 실제 결과에 쓰지 않음): {path.name}")
        return False
    if run.get("display") and not force:
        log(f"  건너뜀 (이미 있음): {path.name}")
        return False
    run["display"] = run_editor(run, client)
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    d = run["display"]
    kw = sum(1 for w in d["warnings"] if w["type"] == "keyword_missing")
    tone = sum(1 for w in d["warnings"] if w["type"] == "tone")
    log(f"  {path.name}: 짧은 글 {len(d['lines'])}개 · 원문 유지 {len(d['fallback'])}개 · 숫자 빠짐 경고 {kw}개 · 말투 경고 {tone}개")
    return True


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="화면용 짧은 글 만들기 (편집자)")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--model")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    if args.files:
        files = [Path(f) for f in args.files]
    else:
        # 기본: 사이트에 실제로 쓰이는 결과(샘플마다 최신 1개)만. 무료 한도를 아끼기 위해
        from .web import all_runs, latest_per_sample
        files = [RUNS_DIR / f"{r['run_id']}.json" for r in latest_per_sample(all_runs()).values()]
    if not files:
        print("data/runs 폴더에 결과 파일이 없습니다.")
        return 1
    try:
        client = make_client(mock=args.mock, model=args.model)
    except LLMError as e:
        print(f"오류: {e}")
        return 1
    print(f"편집자 실행 ({client.model_name}) · 결과 1개당 AI 1번 호출")
    for f in files:
        try:
            apply(f, client, force=args.force)
        except LLMError as e:
            print(f"  멈춤: {e}")
            return 1
    print("화면 갱신: python -m app.report --demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
