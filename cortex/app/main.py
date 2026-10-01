"""CORTEX V0 CLI.

사용법 (프로젝트 폴더에서):
    python -m app.main --file data/inputs/sample_01.txt
    python -m app.main --file data/inputs/sample_01.txt --mock   # API 없이 시험
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):  # Windows 콘솔 한글 깨짐 방지
    sys.stdout.reconfigure(encoding="utf-8")

from .pipeline import run_pipeline  # noqa: E402
from .report import write_report  # noqa: E402
from .utils.llm import LLMError, make_client  # noqa: E402

LINE = "=" * 56
BAR = {1: "■□□□□", 2: "■■□□□", 3: "■■■□□", 4: "■■■■□", 5: "■■■■■"}


def print_report(run: dict) -> None:
    by_id = {s["id"]: s for s in run["preprocess"]["sentences"]}
    imp = run["impression"]

    print(f"\n{LINE}\n 첫인상\n{LINE}")
    print(f" {imp['archetype']}")
    print(f" - {imp['summary']}")
    if imp["key_contrast"]:
        print(f" - 대조: {imp['key_contrast']}")

    print(f"\n{LINE}\n 문단별 인상 흐름 (1~5)\n{LINE}")
    print("        자신감  열정    긴장감  구체성")
    for p in run["analyzer"]["signals"]["paragraph_scores"]:
        print(f" {p['paragraph_id']}   {BAR[p['confidence']]}  {BAR[p['passion']]}  "
              f"{BAR[p['tension']]}  {BAR[p['concreteness']]}")

    print(f"\n{LINE}\n 문장별 인상 신호\n{LINE}")
    for s in run["analyzer"]["signals"]["sentence_signals"]:
        text = by_id[s["sentence_id"]]["text"]
        short = text if len(text) <= 40 else text[:40] + "…"
        print(f" [{s['sentence_id']}] {s['label']}{'!' * s['intensity']:<3} {short}")

    print(f"\n{LINE}\n 위원회 평가\n{LINE}")
    for r in run["rounds"]["round_0"]:
        scores = ", ".join(f"{c['criterion']} {c['score']}" for c in r["scores"])
        print(f" ▶ {r['persona_id']}: {r['summary']}")
        print(f"   {scores}")

    j = run["judge"]
    print(f"\n{LINE}\n 의장 종합\n{LINE}")
    print(f" {j['overall_summary']}\n")
    for i in j["key_issues"]:
        who = ", ".join(i["raised_by"]) or "?"
        ids = ", ".join(i["evidence_ids"])
        print(f" [{i['priority']}] {i['issue']}  ({who} / {ids})")
    if j["disagreements"]:
        print("\n 의견이 갈린 지점")
        for d in j["disagreements"]:
            print(f"  - {d['topic']}")
            for p in d["positions"]:
                print(f"      {p['persona_id']}: {p['position']}")

    v = run["validation"]
    m = run["metadata"]
    print(f"\n{LINE}")
    print(f" 제외된 근거 {v['invalid_evidence_count']}건 · 경고 {len(v['warnings'])}건 · "
          f"모델 {m['model']} · {m['duration_ms'] / 1000:.1f}초")


def main() -> int:
    parser = argparse.ArgumentParser(description="CORTEX V0 — AI 심의위원회")
    parser.add_argument("--file", help="자기소개서 텍스트 파일 경로")
    parser.add_argument("--mock", action="store_true", help="API 없이 가짜 응답으로 파이프라인만 시험")
    parser.add_argument("--model", help="모델 이름 (기본: .env의 GEMINI_MODEL)")
    parser.add_argument("--v1", action="store_true", help="토론 라운드까지 실행 (AI 9번)")
    parser.add_argument("--single", default="", help="단일 AI 비교도 함께: a, b, ab (각 +1번)")
    parser.add_argument("--out", default=str(ROOT / "data" / "runs"), help="결과 JSON 저장 폴더")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    print(f"{LINE}\n 한눈 · {'V1 토론' if args.v1 else 'V0'}{' + 단일 AI 비교 ' + args.single.upper() if args.single else ''}\n{LINE}")
    path_str = args.file or input("자기소개서 파일 경로: ").strip().strip('"')
    path = Path(path_str)
    if not path.exists():
        print(f"파일을 찾을 수 없습니다: {path}")
        return 1
    text = path.read_text(encoding="utf-8")

    try:
        client = make_client(mock=args.mock, model=args.model)
        run, out_path = run_pipeline(text, client, Path(args.out), source=str(path), v1=args.v1, single_modes=args.single.lower())
    except LLMError as e:
        print(f"\n오류: {e}")
        return 1

    print_report(run)
    report_path = write_report(run)
    print(f" 결과 파일: {out_path}")
    print(f" 결과 화면: {report_path}  (더블클릭해서 브라우저로 열기)\n{LINE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
