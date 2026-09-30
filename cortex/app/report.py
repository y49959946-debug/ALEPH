"""결과 보기 화면 생성기.

run.json 하나를 읽어서, 브라우저로 더블클릭해 열 수 있는 HTML 파일 한 개로 만든다.
외부 라이브러리나 인터넷 없이 동작한다. (AI 호출 없음)

사용법 (프로젝트 폴더에서):
    python -m app.report                          # 가장 최근 결과
    python -m app.report data\\runs\\20260930_103907_001.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "data" / "runs"
REPORTS_DIR = ROOT / "data" / "reports"
PERSONA_FILE = Path(__file__).resolve().parent / "personas.yaml"


def _persona_names() -> dict[str, str]:
    try:
        data = yaml.safe_load(PERSONA_FILE.read_text(encoding="utf-8"))
        return {p["id"]: p["name"] for p in data["personas"]}
    except Exception:
        return {}


def build_html(run: dict) -> str:
    payload = {"run": run, "names": _persona_names()}
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return _TEMPLATE.replace("__DATA__", data)


def write_report(run: dict, out_dir: Path = REPORTS_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run['run_id']}.html"
    path.write_text(build_html(run), encoding="utf-8")
    return path


def _latest_run() -> Path | None:
    runs = sorted(p for p in RUNS_DIR.glob("*.json") if not p.name.startswith("consistency_"))
    return runs[-1] if runs else None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    targets = [Path(a) for a in sys.argv[1:]] or [p for p in [_latest_run()] if p]
    if not targets:
        print("data/runs 폴더에 결과 파일이 없습니다.")
        return 1
    for t in targets:
        run = json.loads(t.read_text(encoding="utf-8"))
        out = write_report(run)
        print(f"결과 화면: {out}")
    return 0


_TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CORTEX 결과</title>
<style>
:root {
  color-scheme: light;
  --bg: #f6f5f2;
  --surface: #fcfcfb;
  --surface-2: #f0efec;
  --line: #e2e0da;
  --text: #1a1917;
  --text-2: #52514e;
  --text-3: #7a7873;
  --accent: #1c5cab;
  --c-conf: #2a78d6;   /* 자신감 */
  --c-pass: #eb6834;   /* 열정 */
  --c-hes:  #1baf7a;   /* 망설임 */
  --hatch:  #8a8780;   /* 방어적 (무늬) */
  --series: #2a78d6;
  --st-high: #d03b3b;
  --st-mid:  #c98500;
  --st-low:  #7a7873;
  --flash: #fff1c2;
  --shadow: 0 1px 2px rgba(20,20,10,.06), 0 4px 16px rgba(20,20,10,.05);
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --bg: #121211; --surface: #1a1a19; --surface-2: #232321; --line: #33332f;
    --text: #f4f3ef; --text-2: #c3c2b7; --text-3: #8f8d85; --accent: #6da7ec;
    --c-conf: #3987e5; --c-pass: #d95926; --c-hes: #199e70; --hatch: #9a978e;
    --series: #3987e5; --st-high: #e66767; --st-mid: #e0a52a; --st-low: #8f8d85;
    --flash: #4a3f1a; --shadow: none;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #121211; --surface: #1a1a19; --surface-2: #232321; --line: #33332f;
  --text: #f4f3ef; --text-2: #c3c2b7; --text-3: #8f8d85; --accent: #6da7ec;
  --c-conf: #3987e5; --c-pass: #d95926; --c-hes: #199e70; --hatch: #9a978e;
  --series: #3987e5; --st-high: #e66767; --st-mid: #e0a52a; --st-low: #8f8d85;
  --flash: #4a3f1a; --shadow: none;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: "Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", system-ui, sans-serif;
  font-size: 15px; line-height: 1.65; -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 880px; margin: 0 auto; padding: 32px 16px 80px; }
header.top { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 28px; }
.brand { font-weight: 800; letter-spacing: .08em; font-size: 13px; color: var(--text-2); }
.brand b { color: var(--text); }
.meta { font-size: 12px; color: var(--text-3); }
.theme-btn { font: inherit; font-size: 12px; color: var(--text-2); background: transparent; border: 1px solid var(--line); border-radius: 999px; padding: 3px 10px; cursor: pointer; }

section { margin-top: 44px; }
.step { font-size: 12px; font-weight: 700; color: var(--accent); letter-spacing: .04em; }
h2 { font-size: 21px; margin: 4px 0 6px; line-height: 1.35; letter-spacing: -.01em; }
.lead { color: var(--text-2); margin: 0 0 18px; font-size: 14px; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: 20px; box-shadow: var(--shadow); }

/* ① 첫인상 */
.hero { padding: 28px 24px; }
.hero .kicker { font-size: 13px; color: var(--text-3); margin-bottom: 8px; }
.hero .archetype { font-size: 26px; font-weight: 800; line-height: 1.35; letter-spacing: -.02em; margin: 0 0 10px; }
.hero .summary { color: var(--text-2); margin: 0; }
.contrast { margin-top: 14px; padding: 10px 14px; border-left: 3px solid var(--accent); background: var(--surface-2); border-radius: 0 8px 8px 0; font-size: 14px; }
.contrast b { font-size: 12px; color: var(--text-3); display: block; }
.evid { margin-top: 12px; font-size: 12px; color: var(--text-3); }
.meters { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px 24px; margin-top: 22px; padding-top: 18px; border-top: 1px solid var(--line); }
.meter .name { font-size: 13px; color: var(--text-2); display: flex; justify-content: space-between; }
.meter .name span { color: var(--text); font-weight: 600; }
.segs { display: flex; gap: 3px; margin-top: 6px; }
.segs i { flex: 1; height: 8px; border-radius: 4px; background: var(--surface-2); }
.segs i.on { background: var(--series); }
.note { font-size: 12px; color: var(--text-3); margin-top: 14px; }

/* 문장 ID 칩 */
.sid { display: inline-block; font-size: 11px; font-weight: 600; font-family: ui-monospace, Consolas, monospace; color: var(--text-2); background: var(--surface-2); border: 1px solid var(--line); border-radius: 6px; padding: 0 5px; margin: 0 2px; cursor: pointer; line-height: 18px; }
.sid:hover { color: var(--accent); border-color: var(--accent); }

/* ② 원문 색칠 */
.legend { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
.lg { font: inherit; font-size: 13px; display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface); color: var(--text); cursor: pointer; }
.lg[aria-pressed="false"] { opacity: .45; }
.lg .n { color: var(--text-3); font-size: 12px; }
.sw { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.doc p { margin: 0 0 18px; }
.role { display: inline-block; font-size: 11px; font-weight: 700; color: var(--text-3); margin-right: 6px; }
.sent { border-radius: 4px; padding: 1px 2px; cursor: pointer; transition: opacity .15s, background-color .15s; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.sent[data-l="자신감"] { background: color-mix(in srgb, var(--c-conf) var(--a), transparent); border-bottom: 2px solid var(--c-conf); }
.sent[data-l="열정"]   { background: color-mix(in srgb, var(--c-pass) var(--a), transparent); border-bottom: 2px solid var(--c-pass); }
.sent[data-l="망설임"] { background: color-mix(in srgb, var(--c-hes)  var(--a), transparent); border-bottom: 2px solid var(--c-hes); }
.sent[data-l="방어적"] { background: repeating-linear-gradient(45deg, color-mix(in srgb, var(--hatch) var(--a), transparent) 0 2px, transparent 2px 6px); border-bottom: 2px dashed var(--hatch); }
.sent[data-l="중립"]   { border-bottom: 1px dotted var(--line); }
.sent.dim { opacity: .28; }
.sent .q { font-weight: 700; }
.tag { font-size: 10.5px; font-weight: 700; color: var(--text-2); vertical-align: 2px; margin: 0 4px 0 2px; white-space: nowrap; }
.sent.flash { animation: flash 1.4s ease-out; }
@keyframes flash { 0%, 40% { box-shadow: 0 0 0 4px var(--flash); } 100% { box-shadow: 0 0 0 0 transparent; } }

/* ③ 인상 흐름 */
.flows { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }
.flow { padding: 14px 14px 8px; }
.flow h3 { font-size: 14px; margin: 0; }
.flow .sub { font-size: 11.5px; color: var(--text-3); margin: 0 0 4px; }
.flow svg { width: 100%; height: auto; display: block; overflow: visible; }
.flow .grid { stroke: var(--line); stroke-width: 1; }
.flow .axis { fill: var(--text-3); font-size: 12px; }
.flow .ln { fill: none; stroke: var(--series); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.flow .dot { fill: var(--series); stroke: var(--surface); stroke-width: 2; pointer-events: none; }
.flow .hit { fill: transparent; cursor: pointer; }
.flow .hit:hover + .dot, .flow .dot.hl { r: 6; }

/* ④ 위원회 */
.council { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 14px; }
.pc h3 { display: flex; align-items: center; gap: 10px; font-size: 16px; margin: 0 0 6px; }
.av { width: 30px; height: 30px; border-radius: 50%; background: var(--surface-2); border: 1px solid var(--line); display: grid; place-items: center; font-size: 13px; font-weight: 800; color: var(--text-2); flex: none; }
.pc .one { font-size: 13.5px; color: var(--text-2); margin: 0 0 12px; }
.crit { list-style: none; padding: 0; margin: 0 0 14px; }
.crit li { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 3px 0; }
.dots { display: inline-flex; gap: 3px; }
.dots i { width: 8px; height: 8px; border-radius: 50%; background: var(--surface-2); border: 1px solid var(--line); }
.dots i.on { background: var(--text-2); border-color: var(--text-2); }
.pc h4 { font-size: 12px; color: var(--text-3); margin: 12px 0 4px; font-weight: 700; }
.pc ul.items { margin: 0; padding-left: 16px; font-size: 13.5px; }
.pc ul.items li { margin-bottom: 6px; }
.pc .why { color: var(--text-3); font-size: 12.5px; display: block; }

/* ⑤ 갈린 지점 */
.split { display: grid; grid-template-columns: 1fr auto 1fr; gap: 12px; align-items: stretch; margin-top: 12px; }
.split .side { background: var(--surface-2); border-radius: 10px; padding: 12px 14px; font-size: 14px; }
.split .who { font-size: 12px; font-weight: 700; color: var(--text-2); margin-bottom: 4px; }
.split .vs { align-self: center; font-size: 12px; font-weight: 800; color: var(--text-3); }
.dis + .dis { margin-top: 16px; }
.dis h3 { font-size: 15px; margin: 0; }
.dis .foot { font-size: 12.5px; color: var(--text-3); margin-top: 10px; }
@media (max-width: 560px) { .split { grid-template-columns: 1fr; } .split .vs { justify-self: center; } }

/* ⑥ 의장 종합 */
.overall { font-size: 15px; margin: 0 0 16px; }
.issue { display: grid; grid-template-columns: 64px 1fr; gap: 12px; padding: 12px 0; border-top: 1px solid var(--line); }
.pri { font-size: 12px; font-weight: 800; display: inline-flex; align-items: center; gap: 5px; }
.pri::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.pri.높음 { color: var(--st-high); } .pri.중간 { color: var(--st-mid); } .pri.낮음 { color: var(--st-low); }
.issue .by { font-size: 12px; color: var(--text-3); margin-top: 4px; }
.keep { margin-top: 18px; font-size: 14px; }
.keep ul { margin: 6px 0 0; padding-left: 18px; }

footer { margin-top: 56px; padding-top: 18px; border-top: 1px solid var(--line); font-size: 12px; color: var(--text-3); }
footer p { margin: 4px 0; }

#tip { position: fixed; z-index: 10; max-width: 300px; pointer-events: none; background: var(--text); color: var(--bg); font-size: 12.5px; line-height: 1.5; padding: 9px 11px; border-radius: 8px; opacity: 0; transition: opacity .1s; box-shadow: 0 6px 20px rgba(0,0,0,.18); }
#tip.show { opacity: 1; }
#tip b { display: block; font-size: 13px; }
#tip .mute { opacity: .75; }
</style>
</head>
<body>
<div class="wrap" id="app"></div>
<div id="tip" role="tooltip"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const { run, names } = JSON.parse(document.getElementById("data").textContent);
  const app = document.getElementById("app");
  const tip = document.getElementById("tip");
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const nameOf = id => names[id] || id;
  const sentences = run.preprocess.sentences;
  const byId = Object.fromEntries(sentences.map(s => [s.id, s]));
  const signals = Object.fromEntries((run.analyzer.signals.sentence_signals || []).map(s => [s.sentence_id, s]));
  const roles = Object.fromEntries((run.analyzer.observations.paragraph_roles || []).map(r => [r.paragraph_id, r.role]));
  const personas = run.rounds.round_0 || [];
  const LABELS = ["자신감", "열정", "망설임", "방어적", "중립"];
  const SW = { "자신감": "var(--c-conf)", "열정": "var(--c-pass)", "망설임": "var(--c-hes)", "중립": "var(--surface-2)" };
  const INT = { 1: "은은함", 2: "뚜렷함", 3: "두드러짐" };
  const ALPHA = { 1: "14%", 2: "24%", 3: "36%" };
  const LEVEL = v => ["", "매우 약함", "약함", "보통", "강함", "매우 강함"][Math.round(v)] || "";
  const chip = id => `<span class="sid" data-go="${esc(id)}">${esc(id)}</span>`;

  // 문장별로 위원회가 언급한 내용 모으기
  const mentions = {};
  personas.forEach(p => {
    const add = (ids, kind, text) => (ids || []).forEach(id => (mentions[id] ||= []).push({ who: nameOf(p.persona_id), kind, text }));
    p.strengths.forEach(x => add(x.evidence_ids, "강점", x.claim));
    p.weaknesses.forEach(x => add(x.evidence_ids, "약점", x.claim));
    p.recommendations.forEach(x => add(x.target_ids, "제안", x.suggestion));
  });

  const imp = run.impression;
  const ps = run.analyzer.signals.paragraph_scores || [];
  const METRICS = [["confidence", "자신감"], ["passion", "열정·몰입"], ["tension", "긴장감"], ["concreteness", "구체성"]];
  const avg = k => ps.length ? ps.reduce((a, p) => a + p[k], 0) / ps.length : 0;
  const source = (run.document.source || "").split(/[\\/]/).pop();
  const created = (run.metadata.created_at || "").replace("T", " ").slice(0, 16);

  let html = `
  <header class="top">
    <div class="brand"><b>CORTEX</b> · AI 심의위원회</div>
    <div class="meta">${esc(source)} · ${esc(created)} <button class="theme-btn" id="theme">밝기 전환</button></div>
  </header>

  <section style="margin-top:0">
    <div class="step">① 첫인상</div>
    <h2>이 글은 이렇게 읽혀요</h2>
    <div class="card hero">
      <div class="kicker">이 글에서 떠오르는 작성자</div>
      <p class="archetype">${esc(imp.archetype)}</p>
      <p class="summary">${esc(imp.summary)}</p>
      ${imp.key_contrast ? `<div class="contrast"><b>글 안에서 어조가 달라지는 곳</b>${esc(imp.key_contrast)}</div>` : ""}
      <div class="evid">근거 문장 ${(imp.evidence_sentence_ids || []).map(chip).join("")}</div>
      <div class="meters">
        ${METRICS.map(([k, label]) => {
          const v = avg(k);
          return `<div class="meter"><div class="name">${label}<span>${LEVEL(v)}</span></div>
            <div class="segs" aria-label="${label} 5단계 중 ${Math.round(v)}">${[1,2,3,4,5].map(i => `<i class="${i <= Math.round(v) ? "on" : ""}"></i>`).join("")}</div></div>`;
        }).join("")}
      </div>
      <div class="note">글에 쓰인 표현과 구조에서 읽히는 인상이에요. 작성자의 성격이나 실제 감정을 판단한 결과가 아니에요.</div>
    </div>
  </section>

  <section>
    <div class="step">② 이유</div>
    <h2>어떤 문장이 그렇게 보이게 했을까?</h2>
    <p class="lead">문장에 마우스를 올리면(휴대폰은 누르면) 왜 그렇게 읽혔는지 보여줘요. 굵은 글씨는 그 인상을 만든 표현이에요. 아래 버튼으로 한 종류만 볼 수 있어요.</p>
    <div class="card">
      <div class="legend" id="legend">
        ${LABELS.map(l => {
          const n = Object.values(signals).filter(s => s.label === l).length;
          const sw = l === "방어적"
            ? `<span class="sw" style="background:repeating-linear-gradient(45deg,var(--hatch) 0 2px,transparent 2px 5px);border:1px solid var(--hatch)"></span>`
            : `<span class="sw" style="background:${SW[l]};${l === "중립" ? "border:1px dotted var(--text-3)" : ""}"></span>`;
          return `<button class="lg" data-l="${l}" aria-pressed="true">${sw}${l}<span class="n">${n}</span></button>`;
        }).join("")}
      </div>
      <div class="doc">
        ${run.preprocess.paragraphs.map(p => `<p><span class="role">${esc(roles[p.id] || p.id)}</span>${
          p.sentence_ids.map(id => {
            const s = byId[id], g = signals[id];
            if (!g) return `<span class="sent" id="${id}" data-l="중립">${esc(s.text)}</span> `;
            let body = esc(s.text);
            const q = esc(g.quote);
            if (q && body.includes(q)) body = body.replace(q, `<span class="q">${q}</span>`);
            return `<span class="sent" id="${id}" data-l="${esc(g.label)}" style="--a:${ALPHA[g.intensity] || "20%"}">${body}</span><span class="tag">${esc(g.label)}${g.label !== "중립" ? "·" + INT[g.intensity] : ""}</span> `;
          }).join("")
        }</p>`).join("")}
      </div>
    </div>
  </section>

  <section>
    <div class="step">③ 흐름</div>
    <h2>글에서 느껴지는 인상은 문단마다 어떻게 달라질까?</h2>
    <p class="lead">문단마다 네 가지 인상이 얼마나 강하게 읽히는지 5단계로 나타냈어요. 점을 가리키면 자세히 보여요.</p>
    <div class="flows">${METRICS.map(([k, label]) => flowChart(k, label)).join("")}</div>
  </section>

  <section>
    <div class="step">④ 세 명의 시선</div>
    <h2>세 평가자는 이 글을 어떻게 봤을까?</h2>
    <p class="lead">세 평가자는 서로의 의견을 보지 않고, 각자 다른 기준으로 따로 평가했어요. 문장 번호를 누르면 원문의 그 문장으로 이동해요.</p>
    <div class="council">${personas.map(personaCard).join("")}</div>
  </section>`;

  const dis = run.judge.disagreements || [];
  if (dis.length) {
    html += `
  <section>
    <div class="step">⑤ 갈린 지점</div>
    <h2>같은 글, 다른 시선</h2>
    <p class="lead">평가 기준이 다르면 같은 부분도 다르게 보여요. 이 차이가 여러 관점으로 읽어보는 이유예요.</p>
    <div class="card">${dis.map(d => `
      <div class="dis"><h3>${esc(d.topic)}</h3>
        <div class="split">${d.positions.map((p, i) => `${i ? '<div class="vs">VS</div>' : ""}<div class="side"><div class="who">${esc(nameOf(p.persona_id))}</div>${esc(p.position)}</div>`).join("")}</div>
      </div>`).join("")}
      <div class="dis foot">어느 쪽이 맞다기보다, 이 글을 누가 읽을지에 따라 무엇을 먼저 고칠지가 달라져요.</div>
    </div>
  </section>`;
  }

  const issues = run.judge.key_issues || [];
  const order = { "높음": 0, "중간": 1, "낮음": 2 };
  html += `
  <section>
    <div class="step">${dis.length ? "⑥" : "⑤"} 정리</div>
    <h2>그래서 무엇을 먼저 고치면 좋을까?</h2>
    <div class="card">
      <p class="overall">${esc(run.judge.overall_summary)}</p>
      ${issues.slice().sort((a, b) => order[a.priority] - order[b.priority]).map(i => `
        <div class="issue"><div><span class="pri ${esc(i.priority)}">${esc(i.priority)}</span></div>
          <div>${esc(i.issue)}<div class="by">${i.raised_by.map(nameOf).map(esc).join(" · ")} 지적 ${(i.evidence_ids || []).map(chip).join("")}</div></div></div>`).join("")}
      ${(run.judge.keep || []).length ? `<div class="keep"><b>그대로 두면 좋은 점</b><ul>${run.judge.keep.map(k => `<li>${esc(k)}</li>`).join("")}</ul></div>` : ""}
    </div>
  </section>

  <footer>
    <p>이 결과는 자기소개서의 품질이나 지원자의 역량을 객관적으로 측정한 것이 아니라, 입력된 글을 여러 관점에서 읽어본 결과예요.</p>
    <p>근거 검증: 원문에 없는 근거 ${run.validation.invalid_evidence_count}건 제외 · 경고 ${run.validation.warnings.length}건</p>
    <p>모델 ${esc(run.metadata.model)} · 실행 ${esc(run.run_id)} · ${Math.round(run.metadata.duration_ms / 1000)}초 · 프롬프트 ${Object.entries(run.metadata.prompt_hashes || {}).map(([f, h]) => esc(f.replace(/\.(txt|yaml)$/, "")) + " " + esc(h.slice(0, 6))).join(", ")}</p>
  </footer>`;

  app.innerHTML = html;

  function flowChart(key, label) {
    const W = 240, H = 130, L = 22, R = 14, T = 12, B = 28;
    const n = ps.length;
    const x = i => n <= 1 ? (L + W - R) / 2 : L + i * (W - L - R) / (n - 1);
    const y = v => T + (5 - v) * (H - T - B) / 4;
    const pts = ps.map((p, i) => [x(i), y(p[key])]);
    const path = pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join(" ");
    const sub = { confidence: "망설임 ↔ 확신", passion: "건조함 ↔ 몰입", tension: "여유 ↔ 방어적", concreteness: "추상적 ↔ 구체적" }[key];
    return `<div class="card flow"><h3>${label}</h3><p class="sub">${sub}</p>
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${label} 문단별 흐름: ${ps.map(p => (roles[p.paragraph_id] || p.paragraph_id) + " " + p[key]).join(", ")}">
        ${[1, 3, 5].map(v => `<line class="grid" x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}"/><text class="axis" x="${L - 6}" y="${y(v) + 3}" text-anchor="end">${v}</text>`).join("")}
        <path class="ln" d="${path}"/>
        ${ps.map((p, i) => `<g data-tip="<b>${esc(roles[p.paragraph_id] || p.paragraph_id)} 문단 · ${label}</b>${LEVEL(p[key])} (5단계 중 ${p[key]})"><circle class="hit" cx="${x(i)}" cy="${y(p[key])}" r="14"/><circle class="dot" cx="${x(i)}" cy="${y(p[key])}" r="4.5"/></g>
          <text class="axis" x="${x(i)}" y="${H - 8}" text-anchor="middle">${esc(roles[p.paragraph_id] || p.paragraph_id)}</text>`).join("")}
      </svg></div>`;
  }

  function personaCard(p) {
    const nm = nameOf(p.persona_id);
    const list = (title, items, fmt) => items.length ? `<h4>${title}</h4><ul class="items">${items.map(fmt).join("")}</ul>` : "";
    return `<div class="card pc">
      <h3><span class="av">${esc(nm.slice(0, 1))}</span>${esc(nm)}</h3>
      <p class="one">${esc(p.summary)}</p>
      <ul class="crit">${p.scores.map(c => `<li>${esc(c.criterion)}<span class="dots" aria-label="5점 중 ${c.score}점" title="5점 중 ${c.score}점">${[1,2,3,4,5].map(i => `<i class="${i <= c.score ? "on" : ""}"></i>`).join("")}</span></li>`).join("")}</ul>
      ${list("좋았던 점", p.strengths, x => `<li>${esc(x.claim)} ${x.evidence_ids.map(chip).join("")}</li>`)}
      ${list("아쉬운 점", p.weaknesses, x => `<li>${esc(x.claim)} ${x.evidence_ids.map(chip).join("")}</li>`)}
      ${list("이렇게 고쳐보면", p.recommendations, x => `<li>${esc(x.suggestion)} ${x.target_ids.map(chip).join("")}<span class="why">${esc(x.reason)}</span></li>`)}
    </div>`;
  }

  // 툴팁
  function showTip(html, ev) {
    tip.innerHTML = html; tip.classList.add("show");
    const r = tip.getBoundingClientRect(), pad = 12;
    let left = ev.clientX + 14, top = ev.clientY + 16;
    if (left + r.width > innerWidth - pad) left = ev.clientX - r.width - 14;
    if (top + r.height > innerHeight - pad) top = ev.clientY - r.height - 14;
    tip.style.left = Math.max(pad, left) + "px"; tip.style.top = Math.max(pad, top) + "px";
  }
  const hideTip = () => tip.classList.remove("show");
  function sentTip(id) {
    const g = signals[id], m = mentions[id] || [];
    let h = g ? `<b>${esc(g.label)} · ${INT[g.intensity] || ""}</b>${esc(g.reason)}` : `<b>인상 신호 없음</b>`;
    if (m.length) h += `<div class="mute" style="margin-top:6px">평가자 언급</div>` + m.slice(0, 4).map(x => `<div>· ${esc(x.who)} (${x.kind})</div>`).join("");
    return h;
  }
  app.addEventListener("mousemove", e => {
    const s = e.target.closest(".sent"), h = e.target.closest("[data-tip]");
    if (s) showTip(sentTip(s.id), e); else if (h) showTip(h.dataset.tip, e); else hideTip();
  });
  app.addEventListener("mouseleave", hideTip);
  app.addEventListener("click", e => {
    const go = e.target.closest("[data-go]");
    if (go) {
      const el = document.getElementById(go.dataset.go);
      if (el) { el.scrollIntoView({ block: "center" }); el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); }
      return;
    }
    const s = e.target.closest(".sent");
    if (s && matchMedia("(hover: none)").matches) { const r = s.getBoundingClientRect(); showTip(sentTip(s.id), { clientX: r.left, clientY: r.bottom }); }
    const lg = e.target.closest(".lg");
    if (lg) {
      const btns = [...document.querySelectorAll(".lg")];
      const onlyThis = btns.every(b => b === lg ? b.getAttribute("aria-pressed") === "true" : b.getAttribute("aria-pressed") === "false");
      btns.forEach(b => b.setAttribute("aria-pressed", onlyThis ? "true" : String(b === lg)));
      const active = new Set(btns.filter(b => b.getAttribute("aria-pressed") === "true").map(b => b.dataset.l));
      document.querySelectorAll(".sent").forEach(el => el.classList.toggle("dim", !active.has(el.dataset.l)));
    }
  });
  addEventListener("scroll", hideTip, { passive: true });

  // 밝기 전환
  document.getElementById("theme").addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
  });
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
