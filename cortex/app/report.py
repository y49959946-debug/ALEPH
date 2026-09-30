"""결과 보기 화면 생성기.

run.json 하나를 읽어서, 브라우저로 더블클릭해 열 수 있는 HTML 파일 한 개로 만든다.
외부 라이브러리나 인터넷 없이 동작한다. (AI 호출 없음)

화면 흐름: 첫인상 → 같은 문장, 다른 판정 → 원문 직접 탐색 → 세 평가자 → 의장 정리
정보는 한 번에 다 펼치지 않고, 누르면서 발견하도록 접어 둔다.

사용법 (프로젝트 폴더에서):
    python -m app.report                          # 가장 최근 결과
    python -m app.report data\\runs\\20260930_103907_001.json
    python -m app.report --demo data\\runs\\20260930_103907_001.json   # 사이트용 데모 페이지 (demo/index.html)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "data" / "runs"
REPORTS_DIR = ROOT / "data" / "reports"
DEMO_DIR = ROOT / "demo"
PERSONA_FILE = Path(__file__).resolve().parent / "personas.yaml"
REPO_URL = "https://github.com/y49959946-debug/ALEPH/tree/main/cortex"


def _personas() -> dict[str, dict]:
    try:
        data = yaml.safe_load(PERSONA_FILE.read_text(encoding="utf-8"))
        return {p["id"]: {"name": p["name"], "criteria": p.get("criteria", [])} for p in data["personas"]}
    except Exception:
        return {}


def build_html(run: dict, demo: bool = False) -> str:
    payload = {"run": run, "personas": _personas(), "demo": demo, "repo": REPO_URL}
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    title = "CORTEX · AI 심의위원회" if demo else f"CORTEX 결과 · {run.get('run_id', '')}"
    return _TEMPLATE.replace("__DATA__", data).replace("__TITLE__", title)


def write_report(run: dict, out_dir: Path = REPORTS_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run['run_id']}.html"
    path.write_text(build_html(run), encoding="utf-8")
    return path


def write_demo(run: dict) -> Path:
    """사이트 '결과물' 메뉴에서 여는 방문자용 데모 페이지. 지어낸 샘플의 결과만 넣는다."""
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    path = DEMO_DIR / "index.html"
    path.write_text(build_html(run, demo=True), encoding="utf-8")
    return path


def _latest_run() -> Path | None:
    runs = sorted(p for p in RUNS_DIR.glob("*.json") if not p.name.startswith("consistency_"))
    return runs[-1] if runs else None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if "--demo" in args:
        args.remove("--demo")
        src = Path(args[0]) if args else _latest_run()
        if not src:
            print("data/runs 폴더에 결과 파일이 없습니다.")
            return 1
        print(f"데모 페이지: {write_demo(json.loads(src.read_text(encoding='utf-8')))}")
        return 0
    targets = [Path(a) for a in args] or [p for p in [_latest_run()] if p]
    if not targets:
        print("data/runs 폴더에 결과 파일이 없습니다.")
        return 1
    for t in targets:
        out = write_report(json.loads(t.read_text(encoding="utf-8")))
        print(f"결과 화면: {out}")
    return 0


_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  color-scheme: light;
  --bg-top: #f8fbff; --bg-bottom: #edf6f4;
  --panel: #ffffff; --panel-2: #f4f8f8; --line: #dfeae6;
  --ink: #1c2a35; --ink-2: #5d7284; --ink-3: #798b9a;
  --accent: #2b6f8a; --accent-soft: #e3f0f4;
  --c-conf: #2a78d6; --c-pass: #eb6834; --c-hes: #1baf7a; --hatch: #8a8f94;
  --good: #1b6e33; --good-soft: #e3f4e8; --warn: #9a5b00; --warn-soft: #fdf0dc; --none: #798b9a;
  --shadow: 0 14px 30px rgba(85, 108, 121, 0.08);
  --select: #1c2a35;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --bg-top: #141a1f; --bg-bottom: #111816;
    --panel: #1b2329; --panel-2: #222c33; --line: #2e3a41;
    --ink: #eef3f6; --ink-2: #b3c1cb; --ink-3: #8b9ba7;
    --accent: #7ab8d0; --accent-soft: #1f3540;
    --c-conf: #3987e5; --c-pass: #d95926; --c-hes: #199e70; --hatch: #9aa3a9;
    --good: #7fd49a; --good-soft: #1d3325; --warn: #f0b861; --warn-soft: #3a2c16; --none: #8b9ba7;
    --shadow: none; --select: #eef3f6;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg-top: #141a1f; --bg-bottom: #111816;
  --panel: #1b2329; --panel-2: #222c33; --line: #2e3a41;
  --ink: #eef3f6; --ink-2: #b3c1cb; --ink-3: #8b9ba7;
  --accent: #7ab8d0; --accent-soft: #1f3540;
  --c-conf: #3987e5; --c-pass: #d95926; --c-hes: #199e70; --hatch: #9aa3a9;
  --good: #7fd49a; --good-soft: #1d3325; --warn: #f0b861; --warn-soft: #3a2c16; --none: #8b9ba7;
  --shadow: none; --select: #eef3f6;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; min-height: 100%; background: linear-gradient(160deg, var(--bg-top) 0%, var(--bg-bottom) 100%); }
body {
  margin: 0; color: var(--ink); min-height: 100vh; background: transparent;
  font-family: "Pretendard", "Inter", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", system-ui, sans-serif;
  font-size: 16px; line-height: 1.7; -webkit-font-smoothing: antialiased; word-break: keep-all;
}
a { color: var(--accent); }
.wrap { max-width: 1040px; margin: 0 auto; padding: 28px 20px 96px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 24px; box-shadow: var(--shadow); }
button { font: inherit; color: inherit; }

/* 상단 */
.topbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 36px; }
.back { font-size: 14px; color: var(--ink-2); text-decoration: none; }
.back:hover { color: var(--ink); }
.brand { font-size: 13px; font-weight: 800; letter-spacing: .12em; color: var(--ink-2); }
.ghost { background: transparent; border: 1px solid var(--line); border-radius: 999px; padding: 4px 12px; font-size: 13px; color: var(--ink-2); cursor: pointer; }

.hero { text-align: center; padding: 8px 0 12px; }
.hero .eyebrow { font-size: 13px; font-weight: 700; color: var(--accent); letter-spacing: .04em; }
.hero h1 { font-size: clamp(26px, 4.4vw, 40px); line-height: 1.3; letter-spacing: -.025em; margin: 10px 0 16px; }
.hero .sub { color: var(--ink-2); margin: 0 auto; max-width: 560px; }
.samples { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin: 24px 0 10px; }
.sample { border: 1px solid var(--ink); background: var(--ink); color: var(--panel); border-radius: 999px; padding: 8px 16px; font-size: 14px; font-weight: 600; }
.sample small { font-weight: 500; opacity: .75; margin-left: 4px; }
.pipeline { font-size: 13px; color: var(--ink-3); margin-top: 8px; }
.pipeline a { margin-left: 6px; }

/* 섹션 */
section.scene { margin-top: 88px; scroll-margin-top: 16px; }
.num { font-size: 13px; font-weight: 800; color: var(--accent); letter-spacing: .06em; }
.scene h2 { font-size: clamp(22px, 3vw, 28px); line-height: 1.35; letter-spacing: -.02em; margin: 6px 0 8px; }
.scene .lead { color: var(--ink-2); margin: 0 0 22px; max-width: 640px; }

/* 01 첫인상 */
.impression { padding: 36px 32px 28px; }
.quote { font-size: clamp(22px, 3.4vw, 30px); font-weight: 800; line-height: 1.45; letter-spacing: -.02em; margin: 0 0 14px; }
.quote::before { content: "“"; color: var(--accent); margin-right: 2px; }
.quote::after { content: "”"; color: var(--accent); margin-left: 2px; }
.impression .summary { color: var(--ink-2); margin: 0; }
.meters { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 28px; }
.meter { background: var(--panel-2); border-radius: 16px; padding: 14px 16px; }
.meter .k { font-size: 13px; color: var(--ink-2); }
.meter .v { font-size: 18px; font-weight: 800; margin: 2px 0 8px; }
.segs { display: flex; gap: 3px; }
.segs i { flex: 1; height: 6px; border-radius: 3px; background: var(--line); }
.segs i.on { background: var(--accent); }
.fine { font-size: 13px; color: var(--ink-3); margin-top: 18px; }
details.more { margin-top: 18px; border-top: 1px solid var(--line); padding-top: 14px; }
details.more > summary { cursor: pointer; font-size: 14px; font-weight: 600; color: var(--ink-2); list-style: none; }
details.more > summary::-webkit-details-marker { display: none; }
details.more > summary::after { content: " ↓"; }
details.more[open] > summary::after { content: " ↑"; }
.flows { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; }
.flow { background: var(--panel-2); border-radius: 16px; padding: 12px 12px 6px; }
.flow h4 { margin: 0; font-size: 13px; }
.flow .sub2 { font-size: 11.5px; color: var(--ink-3); }
.flow svg { width: 100%; height: auto; display: block; overflow: visible; }
.flow .grid { stroke: var(--line); }
.flow .axis { fill: var(--ink-3); font-size: 12px; }
.flow .ln { fill: none; stroke: var(--accent); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.flow .dot { fill: var(--accent); stroke: var(--panel-2); stroke-width: 2; pointer-events: none; }
.flow .hit { fill: transparent; cursor: pointer; }
.contrast { margin-top: 10px; font-size: 14.5px; color: var(--ink-2); }

/* 02 같은 문장, 다른 판정 */
.clash { padding: 32px; }
.clash .target { font-size: clamp(18px, 2.4vw, 21px); font-weight: 700; line-height: 1.6; padding: 18px 22px; background: var(--panel-2); border-radius: 16px; margin: 0 0 22px; }
.clash .target .sid { vertical-align: 3px; margin-right: 8px; }
.verdicts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.verdict { border: 1px solid var(--line); border-radius: 18px; padding: 16px 18px; }
.verdict .who { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
.badge { display: inline-flex; align-items: center; gap: 4px; font-size: 12.5px; font-weight: 700; border-radius: 999px; padding: 2px 10px; margin: 10px 0 8px; }
.badge.good { background: var(--good-soft); color: var(--good); }
.badge.warn { background: var(--warn-soft); color: var(--warn); }
.badge.mixed { background: var(--accent-soft); color: var(--accent); }
.badge.none { background: var(--panel-2); color: var(--none); }
.verdict p { margin: 0; font-size: 14.5px; color: var(--ink-2); }
.verdict p + p { margin-top: 6px; }
.clash .moral { margin: 22px 0 0; font-weight: 700; text-align: center; }
.clash .topic { text-align: center; font-size: 14px; color: var(--ink-3); margin-top: 6px; }
.clash .others { text-align: center; margin-top: 14px; font-size: 13px; color: var(--ink-3); }
.btn { display: inline-block; margin-top: 18px; border: 1px solid var(--line); background: var(--panel); border-radius: 999px; padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer; }
.btn:hover { border-color: var(--accent); color: var(--accent); }
.center { text-align: center; }

/* 03 원문 탐색 */
.explore { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 20px; align-items: start; }
.reader { padding: 24px 28px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 18px; }
.lg { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; padding: 4px 11px; border: 1px solid var(--line); border-radius: 999px; background: var(--panel); cursor: pointer; }
.lg[aria-pressed="false"] { opacity: .4; }
.lg .n { color: var(--ink-3); }
.sw { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
.para { margin: 0 0 22px; font-size: 16.5px; line-height: 2; }
.para:last-child { margin-bottom: 0; }
.role { display: block; font-size: 12px; font-weight: 700; color: var(--ink-3); line-height: 1.4; margin-bottom: 2px; }
.sent { cursor: pointer; border-radius: 6px; padding: 2px 1px; -webkit-box-decoration-break: clone; box-decoration-break: clone; transition: opacity .15s, box-shadow .15s; }
.sent[data-l="자신감"] { background: color-mix(in srgb, var(--c-conf) var(--a), transparent); }
.sent[data-l="열정"] { background: color-mix(in srgb, var(--c-pass) var(--a), transparent); }
.sent[data-l="망설임"] { background: color-mix(in srgb, var(--c-hes) var(--a), transparent); }
.sent[data-l="방어적"] { background: repeating-linear-gradient(45deg, color-mix(in srgb, var(--hatch) var(--a), transparent) 0 2px, transparent 2px 6px); }
.sent:hover { box-shadow: 0 0 0 2px var(--line); }
.sent.sel { box-shadow: 0 0 0 2px var(--select); }
.sent.dim { opacity: .3; }
.sent.flash { animation: flash 1.2s ease-out; }
@keyframes flash { 0%, 35% { box-shadow: 0 0 0 5px color-mix(in srgb, var(--accent) 45%, transparent); } 100% { box-shadow: 0 0 0 2px var(--select); } }
.mark-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--ink-3); vertical-align: 3px; margin-left: 3px; }

.panel { position: sticky; top: 16px; padding: 22px; }
.panel .close { display: none; }
.panel .head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.panel .stext { font-size: 15px; line-height: 1.7; margin: 12px 0 14px; }
.panel h5 { font-size: 12.5px; color: var(--ink-3); margin: 16px 0 6px; font-weight: 700; }
.panel .why { font-size: 14.5px; color: var(--ink-2); margin: 0; }
.panel .why b { color: var(--ink); }
.pv { padding: 10px 0; border-top: 1px solid var(--line); }
.pv:first-of-type { border-top: 0; }
.pv .who { font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 6px; }
.pv .badge { margin: 0 0 0 auto; }
.pv p { margin: 4px 0 0; font-size: 14px; color: var(--ink-2); }
.pv .fix { color: var(--ink); }
.pv .fix::before { content: "→ "; color: var(--accent); }
.hint { font-size: 13px; color: var(--ink-3); margin-top: 14px; }
.scrim { display: none; }

.lab { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; border-radius: 999px; padding: 2px 10px; background: var(--panel-2); }
.sid { display: inline-block; font: 600 12px/20px ui-monospace, SFMono-Regular, Consolas, monospace; color: var(--ink-2); background: var(--panel-2); border: 1px solid var(--line); border-radius: 7px; padding: 0 6px; cursor: pointer; }
.sid:hover { color: var(--accent); border-color: var(--accent); }
.av { width: 28px; height: 28px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); display: inline-grid; place-items: center; font-size: 13px; font-weight: 800; flex: none; }

/* 04 세 평가자 */
.council { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.pc { padding: 22px; }
.pc .who { display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 800; }
.pc .looks { font-size: 13px; color: var(--ink-3); margin: 8px 0 12px; }
.pc .one { margin: 0; font-size: 15px; }
.pc details.more { margin-top: 16px; }
.crit { list-style: none; padding: 0; margin: 12px 0 0; }
.crit li { display: flex; justify-content: space-between; align-items: center; font-size: 13.5px; padding: 3px 0; gap: 8px; }
.dots { display: inline-flex; gap: 3px; flex: none; }
.dots i { width: 7px; height: 7px; border-radius: 50%; background: var(--line); }
.dots i.on { background: var(--ink-2); }
.pc h6 { font-size: 12.5px; color: var(--ink-3); margin: 16px 0 4px; }
.pc ul.items { margin: 0; padding-left: 18px; font-size: 14px; color: var(--ink-2); }
.pc ul.items li { margin-bottom: 6px; }

/* 05 의장 */
.chair { padding: 30px 32px; }
.chair .overall { margin: 0 0 24px; color: var(--ink-2); }
.cols { display: grid; grid-template-columns: 1fr 1.4fr; gap: 28px; }
.cols h3 { font-size: 15px; margin: 0 0 10px; }
.keep { list-style: none; margin: 0; padding: 0; }
.keep li { background: var(--good-soft); color: var(--ink); border-radius: 14px; padding: 12px 14px; font-size: 14.5px; margin-bottom: 8px; }
.fixes { list-style: none; margin: 0; padding: 0; counter-reset: fx; }
.fixes li { counter-increment: fx; display: grid; grid-template-columns: 34px 1fr; gap: 8px; padding: 12px 0; border-top: 1px solid var(--line); }
.fixes li:first-child { border-top: 0; padding-top: 0; }
.fixes li::before { content: counter(fx, decimal-leading-zero); font-weight: 800; color: var(--accent); }
.fixes .meta { font-size: 13px; color: var(--ink-3); margin-top: 4px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.pri { font-size: 12px; font-weight: 800; border-radius: 999px; padding: 0 8px; }
.pri.높음 { background: var(--warn-soft); color: var(--warn); }
.pri.중간 { background: var(--accent-soft); color: var(--accent); }
.pri.낮음 { background: var(--panel-2); color: var(--ink-3); }

footer { margin-top: 72px; text-align: center; color: var(--ink-2); }
footer .closing { font-size: 17px; font-weight: 700; color: var(--ink); max-width: 560px; margin: 0 auto 8px; }
footer details { margin-top: 24px; font-size: 13px; color: var(--ink-3); }
footer details summary { cursor: pointer; }
footer details p { margin: 4px 0; }

#tip { position: fixed; z-index: 30; max-width: 260px; pointer-events: none; background: var(--ink); color: var(--panel); font-size: 12.5px; line-height: 1.5; padding: 8px 10px; border-radius: 8px; opacity: 0; transition: opacity .1s; }
#tip.show { opacity: 1; }

@media (max-width: 860px) {
  .meters, .flows { grid-template-columns: repeat(2, 1fr); }
  .verdicts, .council { grid-template-columns: 1fr; }
  .cols { grid-template-columns: 1fr; }
  .explore { grid-template-columns: 1fr; }
  .impression, .clash, .chair { padding: 24px 20px; }
  .reader { padding: 20px; }
  /* 휴대폰: 문장 상세는 아래에서 올라오는 시트 */
  .panel { position: fixed; left: 0; right: 0; bottom: 0; top: auto; z-index: 20; max-height: 72vh; overflow: auto;
           border-radius: 22px 22px 0 0; transform: translateY(105%); transition: transform .25s ease; box-shadow: 0 -10px 30px rgba(0,0,0,.18); }
  .panel.open { transform: translateY(0); }
  .panel .close { display: block; position: absolute; top: 12px; right: 14px; border: 0; background: var(--panel-2); width: 32px; height: 32px; border-radius: 50%; font-size: 18px; cursor: pointer; }
  .scrim { position: fixed; inset: 0; background: rgba(10, 20, 25, .35); z-index: 19; }
  .scrim.open { display: block; }
  .hint.desk { display: none; }
}
@media (min-width: 861px) { .hint.mob { display: none; } }
</style>
</head>
<body>
<div class="wrap" id="app"></div>
<div class="scrim" id="scrim"></div>
<div id="tip" role="tooltip"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const { run, personas: PMETA, demo, repo } = JSON.parse(document.getElementById("data").textContent);
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const nameOf = id => (PMETA[id] && PMETA[id].name) || id;
  const chip = id => `<span class="sid" data-go="${esc(id)}">${esc(id)}</span>`;

  const sentences = run.preprocess.sentences;
  const byId = Object.fromEntries(sentences.map(s => [s.id, s]));
  const signals = Object.fromEntries((run.analyzer.signals.sentence_signals || []).map(s => [s.sentence_id, s]));
  const roles = Object.fromEntries((run.analyzer.observations.paragraph_roles || []).map(r => [r.paragraph_id, r.role]));
  const ps = run.analyzer.signals.paragraph_scores || [];
  const council = run.rounds.round_0 || [];
  const imp = run.impression;
  const judge = run.judge;

  const LABELS = ["자신감", "열정", "망설임", "방어적", "중립"];
  const SW = { "자신감": "var(--c-conf)", "열정": "var(--c-pass)", "망설임": "var(--c-hes)" };
  const ALPHA = { 1: "13%", 2: "22%", 3: "32%" };
  const INT = { 1: "은은하게", 2: "뚜렷하게", 3: "두드러지게" };
  const LEVEL = v => ["", "매우 약함", "약함", "보통", "강함", "매우 강함"][Math.round(v)] || "";
  const METRICS = [["confidence", "자신감", "망설임 ↔ 확신"], ["passion", "열정·몰입", "건조함 ↔ 몰입"], ["tension", "긴장감", "여유 ↔ 방어적"], ["concreteness", "구체성", "추상적 ↔ 구체적"]];
  const avg = k => ps.length ? ps.reduce((a, p) => a + p[k], 0) / ps.length : 0;
  const swatch = l => l === "방어적"
    ? `<span class="sw" style="background:repeating-linear-gradient(45deg,var(--hatch) 0 2px,transparent 2px 5px);border:1px solid var(--hatch)"></span>`
    : l === "중립" ? `<span class="sw" style="border:1px dashed var(--ink-3)"></span>` : `<span class="sw" style="background:${SW[l]}"></span>`;

  // 문장별로 평가자가 무엇이라고 했는지 모으기 (같은 문장, 다른 판정을 찾는 데이터)
  const byS = {};
  council.forEach(p => {
    const slot = id => ((byS[id] ||= {})[p.persona_id] ||= { good: [], bad: [], fix: [] });
    p.strengths.forEach(x => x.evidence_ids.forEach(id => slot(id).good.push(x.claim)));
    p.weaknesses.forEach(x => x.evidence_ids.forEach(id => slot(id).bad.push(x.claim)));
    p.recommendations.forEach(x => x.target_ids.forEach(id => slot(id).fix.push(x.suggestion)));
  });
  const verdictOf = v => !v || (!v.good.length && !v.bad.length) ? "none" : v.good.length && v.bad.length ? "mixed" : v.good.length ? "good" : "warn";
  const BADGE = { good: "✓ 강점으로 봄", warn: "△ 아쉬운 점으로 봄", mixed: "± 강점과 아쉬움 모두", none: "– 언급하지 않음" };

  // 한 평가자는 강점, 다른 평가자는 아쉬움으로 본 문장 = 의견이 갈린 문장
  const clashes = Object.entries(byS).map(([id, m]) => {
    const vs = council.map(p => verdictOf(m[p.persona_id]));
    const pos = vs.some(v => v === "good" || v === "mixed"), neg = vs.some(v => v === "warn" || v === "mixed");
    const distinct = council.some((a, i) => council.some((b, j) => i !== j && ["good", "mixed"].includes(vs[i]) && ["warn", "mixed"].includes(vs[j])));
    return { id, vs, score: (distinct ? 10 : 0) + vs.filter(v => v !== "none").length + (pos && neg ? 1 : 0), distinct };
  }).filter(c => c.distinct).sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
  const focus = clashes[0] ? clashes[0].id : (sentences[0] && sentences[0].id);

  const source = (run.document.source || "").split(/[\\/]/).pop();
  let h = "";

  // ---------- 상단 ----------
  h += `<div class="topbar">${demo ? `<a class="back" href="../../index.html">← 행로로 돌아가기</a>` : `<span class="brand">CORTEX</span>`}
    <button class="ghost" id="theme" type="button">밝기 전환</button></div>
  <header class="hero">
    <div class="eyebrow">CORTEX · AI 심의위원회</div>
    <h1>하나의 자기소개서를<br>세 가지 시선으로 읽으면<br>무엇이 다르게 보일까요?</h1>
    <p class="sub">채용 담당자, 기술 전문가, 일반 독자 역할의 AI가 서로의 의견을 모른 채 같은 글을 따로 평가했어요.</p>
    <div class="samples"><span class="sample">${demo ? "샘플 1 · 백엔드 개발자 자기소개서" : esc(source || run.run_id)}${demo ? "<small>지어낸 글</small>" : ""}</span></div>
    <div class="pipeline">인상 분석 → 세 평가자의 독립 평가 → 근거 확인 → 의장 정리${demo ? `<a href="${esc(repo)}" target="_blank" rel="noopener">코드 보기 ↗</a>` : ""}</div>
  </header>`;

  // ---------- 01 첫인상 ----------
  h += `<section class="scene" id="s-imp"><div class="num">01</div><h2>이 글은 이렇게 읽혀요</h2>
    <div class="card impression">
      <p class="quote">${esc(imp.archetype)}</p>
      <p class="summary">${esc(imp.summary)}</p>
      <div class="meters">${METRICS.map(([k, label]) => { const v = avg(k); return `<div class="meter"><div class="k">${label}</div><div class="v">${LEVEL(v)}</div><div class="segs" aria-label="${label} 5단계 중 ${Math.round(v)}">${[1,2,3,4,5].map(i => `<i class="${i <= Math.round(v) ? "on" : ""}"></i>`).join("")}</div></div>`; }).join("")}</div>
      <p class="fine">글에 쓰인 표현에서 읽히는 인상이에요. 쓴 사람의 성격이나 실제 감정을 판단한 결과가 아니에요.</p>
      <details class="more"><summary>문단마다 인상이 어떻게 달라지는지 보기</summary>
        <div class="flows">${METRICS.map(([k, label, sub]) => flow(k, label, sub)).join("")}</div>
        ${imp.key_contrast ? `<p class="contrast"><b>어조가 달라지는 곳</b> · ${esc(imp.key_contrast)}</p>` : ""}
      </details>
    </div></section>`;

  // ---------- 02 같은 문장, 다른 판정 ----------
  const dis = judge.disagreements || [];
  if (clashes.length) {
    const c = clashes[0], m = byS[c.id];
    h += `<section class="scene" id="s-clash"><div class="num">02 · 핵심 장면</div><h2>같은 문장인데, 판정이 갈렸어요</h2>
      <p class="lead">세 평가자는 서로의 의견을 보지 못했어요. 그런데 이 문장 하나를 두고 서로 다른 것을 봤어요.</p>
      <div class="card clash">
        <p class="target">${chip(c.id)}${esc(byId[c.id].text)}</p>
        <div class="verdicts">${council.map((p, i) => { const v = m[p.persona_id]; const kind = c.vs[i];
          const lines = !v ? [] : [...v.good.slice(0, 1), ...v.bad.slice(0, 1)];
          return `<div class="verdict"><div class="who"><span class="av">${esc(nameOf(p.persona_id)[0])}</span>${esc(nameOf(p.persona_id))}</div>
            <span class="badge ${kind}">${BADGE[kind]}</span>${lines.length ? lines.map(t => `<p>${esc(t)}</p>`).join("") : `<p>이 문장은 평가 기준과 관련이 적다고 봤어요.</p>`}</div>`; }).join("")}</div>
        <p class="moral">평가 기준이 다르면, 같은 문장에서도 다른 것이 보여요.</p>
        ${dis[0] ? `<p class="topic">의장이 정리한 쟁점 · ${esc(dis[0].topic)}</p>` : ""}
        <div class="center"><button class="btn" data-go="${c.id}" type="button">원문에서 이 문장 살펴보기 ↓</button></div>
        ${clashes.length > 1 ? `<p class="others">판정이 갈린 문장이 ${clashes.length - 1}개 더 있어요 ${clashes.slice(1, 4).map(x => chip(x.id)).join(" ")}</p>` : ""}
      </div></section>`;
  } else if (dis.length) {
    h += `<section class="scene" id="s-clash"><div class="num">02 · 핵심 장면</div><h2>여기서 의견이 갈렸어요</h2>
      <div class="card clash"><div class="verdicts">${dis[0].positions.map(p => `<div class="verdict"><div class="who"><span class="av">${esc(nameOf(p.persona_id)[0])}</span>${esc(nameOf(p.persona_id))}</div><p style="margin-top:10px">${esc(p.position)}</p></div>`).join("")}</div>
      <p class="moral">${esc(dis[0].topic)}</p></div></section>`;
  }

  // ---------- 03 원문 탐색 ----------
  const counts = l => Object.values(signals).filter(s => s.label === l).length;
  h += `<section class="scene" id="s-read"><div class="num">03</div><h2>직접 읽어보세요</h2>
    <p class="lead">문장을 누르면 그 문장이 어떻게 읽혔는지, 세 평가자가 뭐라고 했는지 볼 수 있어요. 점(•)이 붙은 문장은 평가자가 언급한 문장이에요.</p>
    <div class="explore">
      <div class="card reader">
        <div class="legend">${LABELS.map(l => `<button class="lg" type="button" data-l="${l}" aria-pressed="true">${swatch(l)}${l}<span class="n">${counts(l)}</span></button>`).join("")}</div>
        ${run.preprocess.paragraphs.map(p => `<p class="para"><span class="role">${esc(roles[p.id] || "")}</span>${p.sentence_ids.map(id => {
          const g = signals[id]; const mentioned = !!byS[id];
          return `<span class="sent" id="${id}" data-l="${esc(g ? g.label : "중립")}" style="--a:${g ? ALPHA[g.intensity] || "18%" : "0%"}" tabindex="0" role="button">${esc(byId[id].text)}${mentioned ? '<span class="mark-dot" aria-hidden="true"></span>' : ""}</span> `;
        }).join("")}</p>`).join("")}
      </div>
      <aside class="card panel" id="panel" aria-live="polite"></aside>
    </div></section>`;

  // ---------- 04 세 평가자 ----------
  h += `<section class="scene" id="s-council"><div class="num">04</div><h2>세 평가자는 무엇을 봤을까요?</h2>
    <p class="lead">같은 글을 읽었지만, 보는 기준이 달랐어요.</p>
    <div class="council">${council.map(p => {
      const crit = (PMETA[p.persona_id] && PMETA[p.persona_id].criteria) || p.scores.map(s => s.criterion);
      const list = (t, arr, f) => arr.length ? `<h6>${t}</h6><ul class="items">${arr.map(f).join("")}</ul>` : "";
      return `<div class="card pc"><div class="who"><span class="av">${esc(nameOf(p.persona_id)[0])}</span>${esc(nameOf(p.persona_id))}</div>
        <div class="looks">보는 기준 · ${crit.slice(0, 3).map(esc).join(", ")}${crit.length > 3 ? " 등" : ""}</div>
        <p class="one">${esc(p.summary)}</p>
        <details class="more"><summary>자세히 보기</summary>
          <ul class="crit">${p.scores.map(s => `<li>${esc(s.criterion)}<span class="dots" title="5점 중 ${s.score}점" aria-label="5점 중 ${s.score}점">${[1,2,3,4,5].map(i => `<i class="${i <= s.score ? "on" : ""}"></i>`).join("")}</span></li>`).join("")}</ul>
          ${list("좋았던 점", p.strengths, x => `<li>${esc(x.claim)} ${x.evidence_ids.map(chip).join(" ")}</li>`)}
          ${list("아쉬운 점", p.weaknesses, x => `<li>${esc(x.claim)} ${x.evidence_ids.map(chip).join(" ")}</li>`)}
          ${list("이렇게 고쳐보면", p.recommendations, x => `<li>${esc(x.suggestion)} ${x.target_ids.map(chip).join(" ")}</li>`)}
        </details></div>`;
    }).join("")}</div></section>`;

  // ---------- 05 의장 정리 ----------
  const order = { "높음": 0, "중간": 1, "낮음": 2 };
  const issues = (judge.key_issues || []).slice().sort((a, b) => order[a.priority] - order[b.priority]);
  const keep = judge.keep || [];
  h += `<section class="scene" id="s-chair"><div class="num">05</div><h2>세 시선을 합치면</h2>
    <div class="card chair"><p class="overall">${esc(judge.overall_summary)}</p>
      <div class="cols">
        <div><h3>그대로 두세요</h3><ul class="keep">${keep.slice(0, 3).map(k => `<li>${esc(k)}</li>`).join("")}</ul>
          ${keep.length > 3 ? `<details class="more"><summary>${keep.length - 3}개 더 보기</summary><ul class="keep" style="margin-top:10px">${keep.slice(3).map(k => `<li>${esc(k)}</li>`).join("")}</ul></details>` : ""}</div>
        <div><h3>먼저 고치면 좋은 점</h3><ol class="fixes">${issues.map(i => `<li><div>${esc(i.issue)}
          <div class="meta"><span class="pri ${esc(i.priority)}">${esc(i.priority)}</span>${i.raised_by.map(nameOf).map(esc).join(" · ")} ${(i.evidence_ids || []).map(chip).join(" ")}</div></div></li>`).join("")}</ol></div>
      </div></div></section>`;

  // ---------- 마무리 ----------
  const hashes = Object.entries(run.metadata.prompt_hashes || {}).map(([f, x]) => esc(f.replace(/\.(txt|yaml)$/, "")) + " " + esc(String(x).slice(0, 6))).join(", ");
  h += `<footer><p class="closing">CORTEX는 점수를 매기려는 게 아니라, 한 사람의 시선이 놓치는 부분을 여러 시선으로 찾아보려는 실험이에요.</p>
    <p style="font-size:14px">이 결과는 글의 품질이나 지원자의 역량을 객관적으로 측정한 것이 아니에요.</p>
    <details><summary>실험 정보</summary>
      <p>모델 ${esc(run.metadata.model)} · ${Math.round(run.metadata.duration_ms / 1000)}초 · 실행 ${esc(run.run_id)}</p>
      <p>근거 검증: 원문에 없는 근거 ${run.validation.invalid_evidence_count}건 제외 · 경고 ${run.validation.warnings.length}건</p>
      <p>프롬프트 버전 ${hashes}</p>
    </details></footer>`;

  $("#app").innerHTML = h;

  // ---------- 상세 패널 ----------
  const panel = $("#panel"), scrim = $("#scrim");
  const mobile = () => matchMedia("(max-width: 860px)").matches;
  function renderPanel(id) {
    const s = byId[id], g = signals[id], m = byS[id] || {};
    const lab = g ? `<span class="lab">${swatch(g.label)}${esc(g.label)}${g.label !== "중립" ? " · " + INT[g.intensity] : ""}</span>` : "";
    let quoteHtml = esc(g && g.quote ? g.quote : "");
    panel.innerHTML = `<button class="close" type="button" aria-label="닫기">×</button>
      <div class="head">${chip(id)} ${lab}</div>
      <p class="stext">${esc(s.text)}</p>
      ${g ? `<h5>왜 이렇게 읽혔을까요?</h5><p class="why">${g.quote ? `<b>“${quoteHtml}”</b> ` : ""}${esc(g.reason)}</p>` : ""}
      <h5>세 평가자는</h5>
      ${council.map(p => { const v = m[p.persona_id], kind = verdictOf(v);
        return `<div class="pv"><div class="who"><span class="av">${esc(nameOf(p.persona_id)[0])}</span>${esc(nameOf(p.persona_id))}<span class="badge ${kind}">${BADGE[kind]}</span></div>
          ${v ? [...v.good.slice(0, 1), ...v.bad.slice(0, 1)].map(t => `<p>${esc(t)}</p>`).join("") + v.fix.slice(0, 1).map(t => `<p class="fix">${esc(t)}</p>`).join("") : ""}</div>`; }).join("")}
      <p class="hint desk">다른 문장을 눌러보세요.</p>`;
  }
  function select(id, { scroll = false, open = false } = {}) {
    if (!byId[id]) return;
    document.querySelectorAll(".sent.sel").forEach(e => e.classList.remove("sel"));
    const el = document.getElementById(id);
    el.classList.add("sel");
    renderPanel(id);
    if (scroll) { el.scrollIntoView({ block: "center" }); el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); }
    if (open && mobile()) { panel.classList.add("open"); scrim.classList.add("open"); panel.scrollTop = 0; }
  }
  const closeSheet = () => { panel.classList.remove("open"); scrim.classList.remove("open"); };
  select(focus);

  // ---------- 그래프 ----------
  function flow(key, label, sub) {
    const W = 220, H = 120, L = 20, R = 12, T = 10, B = 26, n = ps.length;
    const x = i => n <= 1 ? (L + W - R) / 2 : L + i * (W - L - R) / (n - 1);
    const y = v => T + (5 - v) * (H - T - B) / 4;
    const d = ps.map((p, i) => (i ? "L" : "M") + x(i).toFixed(1) + " " + y(p[key]).toFixed(1)).join(" ");
    return `<div class="flow"><h4>${label}</h4><div class="sub2">${sub}</div>
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${label}: ${ps.map(p => (roles[p.paragraph_id] || p.paragraph_id) + " " + p[key]).join(", ")}">
      ${[1, 3, 5].map(v => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="axis" x="${L - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`).join("")}
      <path class="ln" d="${d}"/>
      ${ps.map((p, i) => `<g data-tip="${esc(roles[p.paragraph_id] || p.paragraph_id)} 문단 · ${LEVEL(p[key])}"><circle class="hit" cx="${x(i)}" cy="${y(p[key])}" r="13"/><circle class="dot" cx="${x(i)}" cy="${y(p[key])}" r="4.5"/></g><text class="axis" x="${x(i)}" y="${H - 6}" text-anchor="middle">${esc(roles[p.paragraph_id] || "")}</text>`).join("")}
      </svg></div>`;
  }

  // ---------- 상호작용 ----------
  const tip = $("#tip");
  document.addEventListener("mousemove", e => {
    const t = e.target.closest && e.target.closest("[data-tip]");
    if (!t) return tip.classList.remove("show");
    tip.textContent = t.dataset.tip; tip.classList.add("show");
    tip.style.left = Math.min(innerWidth - tip.offsetWidth - 10, e.clientX + 12) + "px"; tip.style.top = (e.clientY + 14) + "px";
  });
  document.addEventListener("click", e => {
    const go = e.target.closest("[data-go]");
    if (go) { e.preventDefault(); select(go.dataset.go, { scroll: true, open: true }); return; }
    const s = e.target.closest(".sent");
    if (s) { select(s.id, { open: true }); return; }
    if (e.target.closest(".close") || e.target === scrim) { closeSheet(); return; }
    const lg = e.target.closest(".lg");
    if (lg) {
      const btns = [...document.querySelectorAll(".lg")];
      const only = btns.every(b => (b === lg) === (b.getAttribute("aria-pressed") === "true"));
      btns.forEach(b => b.setAttribute("aria-pressed", only ? "true" : String(b === lg)));
      const on = new Set(btns.filter(b => b.getAttribute("aria-pressed") === "true").map(b => b.dataset.l));
      document.querySelectorAll(".sent").forEach(el => el.classList.toggle("dim", !on.has(el.dataset.l)));
    }
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeSheet();
    if ((e.key === "Enter" || e.key === " ") && e.target.classList && e.target.classList.contains("sent")) { e.preventDefault(); select(e.target.id, { open: true }); }
  });
  $("#theme").addEventListener("click", () => {
    const r = document.documentElement;
    const dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    r.dataset.theme = dark ? "light" : "dark";
  });
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
