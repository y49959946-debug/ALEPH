"""화면 생성기 (AI 호출 없음).

한 페이지 안에서 세 단계로 넘어간다.
- 글 넣기: 샘플을 고르거나 자기소개서를 붙여 넣는다
- 심의: 분석가·세 평가자·의장이 채팅처럼 차례로 말하는 애니메이션
- 결과: 대시보드 (첫인상, 어조 분포, 평가자별 점수, 먼저 고칠 것, 판정이 갈린 문장, 원문 지도)

공개 사이트(demo/)에는 미리 돌려 둔 샘플 결과만 넣는다.
로컬 서버(app/server.py)는 같은 화면을 쓰되, 글 넣기에서 실제로 분석을 돌린다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent / "screens"
RUNS_DIR = ROOT / "data" / "runs"
INPUTS_DIR = ROOT / "data" / "inputs"
DEMO_DIR = ROOT / "demo"
PERSONA_FILE = Path(__file__).resolve().parent / "personas.yaml"
REPO_URL = "https://github.com/y49959946-debug/ALEPH/tree/main/cortex"

SAMPLE_NOTES = {
    "sample_01": "문제·해결·수치가 분명한 글 · 백엔드",
    "sample_02": "상투어가 많고 변명조 · 직무 불명",
    "sample_03": "기술만 나열 · 인프라",
    "sample_04": "경험은 많지만 결과가 없음 · 프론트엔드",
    "sample_05": "수치는 있지만 과정이 없음 · 데이터",
    "sample_06": "감정 표현이 강함 · 모바일",
    "sample_07": "지나치게 겸손함 · QA",
    "sample_08": "문장이 장황함 · 인프라",
    "sample_09": "짧고 간결함 · 백엔드",
    "sample_10": "장점과 약점이 섞임 · 풀스택",
}

LENS = {
    "recruiter": "무엇을 했고, 어떤 결과를 냈는지를 봐요.",
    "technical": "어떤 문제를 어떤 기술로, 왜 그렇게 풀었는지를 봐요.",
    "reader": "개발 용어에 익숙하지 않은 다른 부서 면접관의 시선으로, 이해되고 기억에 남는지를 봐요.",
}


def personas() -> dict[str, dict]:
    try:
        data = yaml.safe_load(PERSONA_FILE.read_text(encoding="utf-8"))
        return {
            p["id"]: {"name": p["name"], "criteria": p.get("criteria", []), "lens": LENS.get(p["id"], "")}
            for p in data["personas"]
        }
    except Exception:
        return {}


def sample_name(run: dict) -> str | None:
    m = re.search(r"(sample_\d+)", run.get("document", {}).get("source", ""))
    return m.group(1) if m else None


def slim(run: dict) -> dict:
    """화면에 필요한 것만 남긴다 (프롬프트 해시 등 제외)."""
    obs = run.get("analyzer", {}).get("observations", {})
    return {
        "run_id": run.get("run_id"),
        "sample": sample_name(run),
        "sentences": [
            {"id": s["id"], "p": s["paragraph_id"], "text": s["text"]} for s in run["preprocess"]["sentences"]
        ],
        "roles": {r["paragraph_id"]: r["role"] for r in obs.get("paragraph_roles", [])},
        "signals": run.get("analyzer", {}).get("signals", {}),
        "impression": run.get("impression", {}),
        "personas": run.get("rounds", {}).get("round_0", []),
        "judge": run.get("judge", {}),
        "invalid": run.get("validation", {}).get("invalid_evidence_count", 0),
        "display": (run.get("display") or {}).get("lines", {}),
        "display_model": (run.get("display") or {}).get("model"),
        "display_warn": len([w for w in (run.get("display") or {}).get("warnings", []) if w.get("type") == "keyword_missing"]),
        "model": run.get("metadata", {}).get("model"),
        "created_at": run.get("metadata", {}).get("created_at"),
    }


def all_runs() -> list[dict]:
    files = sorted(p for p in RUNS_DIR.glob("*.json") if not p.name.startswith("consistency_"))
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            continue
    return out


def latest_per_sample(runs: list[dict]) -> dict[str, dict]:
    """샘플마다 가장 최근 결과 1개. (run_id가 시간순이라 뒤에 오는 것이 최신)
    --mock(가짜 응답) 결과는 실제 결과를 덮어쓰지 않도록 뺀다."""
    out: dict[str, dict] = {}
    for r in sorted(runs, key=lambda r: r.get("run_id", "")):
        name = sample_name(r)
        if name and r.get("metadata", {}).get("model") != "mock":
            out[name] = r
    return out


def samples() -> list[dict]:
    out = []
    for f in sorted(INPUTS_DIR.glob("sample_*.txt")):
        out.append({"id": f.stem, "note": SAMPLE_NOTES.get(f.stem, ""), "text": f.read_text(encoding="utf-8").strip()})
    return out


def _render(name: str, payload: dict) -> str:
    html = (WEB_DIR / name).read_text(encoding="utf-8")
    css = (WEB_DIR / "base.css").read_text(encoding="utf-8")
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return html.replace("/*__CSS__*/", css).replace("__DATA__", data)


def build_page(runs: dict[str, dict], local: bool = False) -> str:
    """한 페이지 안에서 글 넣기 → 심의(채팅) → 결과(대시보드)로 넘어간다.
    runs: 화면에 넣을 결과 {키: run}. 키는 샘플 이름 또는 run_id."""
    slim_runs = {k: slim(r) for k, r in runs.items()}
    ready = sorted({v["sample"] for v in slim_runs.values() if v["sample"]})
    return _render("app.html", {
        "local": local, "repo": REPO_URL, "samples": samples(), "ready": ready,
        "runs": slim_runs, "personas": personas(), "notes": SAMPLE_NOTES,
    })


# 예전 주소(view.html)로 들어와도 같은 화면의 결과로 보낸다
_REDIRECT = """<!doctype html><meta charset="utf-8"><title>CORTEX</title>
<script>var q=new URLSearchParams(location.search);if(!q.get("view"))q.set("view","result");location.replace("index.html?"+q.toString());</script>
<a href="index.html">CORTEX로 이동</a>"""


def write_demo(runs: list[dict] | None = None) -> list[Path]:
    """사이트용 데모: 샘플마다 최신 결과만 넣는다. 지어낸 샘플만 공개한다."""
    chosen = latest_per_sample(runs if runs is not None else all_runs())
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    index, view = DEMO_DIR / "index.html", DEMO_DIR / "view.html"
    index.write_text(build_page(chosen, local=False), encoding="utf-8")
    view.write_text(_REDIRECT, encoding="utf-8")
    return [index, view]
