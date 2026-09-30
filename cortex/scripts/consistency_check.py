"""인상 라벨 일관성 테스트 (개발용).

같은 글을 Analyzer에 N번 넣고, 문장별 라벨이 얼마나 같게 나오는지 잰다.
- 일치율 80%는 잠정 목표일 뿐 통과/탈락 기준이 아니다.
- 일관성 ≠ 정확성. 매번 같아도 틀릴 수 있으니 일부는 사람이 직접 확인한다.

사용법 (프로젝트 폴더에서):
    python -m scripts.consistency_check data/inputs/sample_01.txt --runs 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agents import analyzer  # noqa: E402
from app.preprocess import preprocess  # noqa: E402
from app.utils.llm import make_client  # noqa: E402
from app.utils.validate import Validator  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--pause", type=float, default=4.0, help="호출 사이 대기(초). 무료 티어 분당 한도 대비")
    args = ap.parse_args()
    load_dotenv(ROOT / ".env")
    client = make_client(mock=args.mock)

    report = {"model": client.model_name, "runs": args.runs, "files": {}}
    for f in args.files:
        pre = preprocess(Path(f).read_text(encoding="utf-8"))
        labels: dict[str, list[str]] = {s.id: [] for s in pre.sentences}
        para: dict[str, dict[str, list[int]]] = {}
        print(f"\n{f}: 문장 {len(pre.sentences)}개 × {args.runs}회")
        for i in range(args.runs):
            out = Validator(pre).analyzer(analyzer.run(client, pre))
            for s in out.signals.sentence_signals:
                labels[s.sentence_id].append(s.label)
            for p in out.signals.paragraph_scores:
                d = para.setdefault(p.paragraph_id, {k: [] for k in ("confidence", "passion", "tension", "concreteness")})
                for k in d:
                    d[k].append(getattr(p, k))
            print(f"  {i + 1}/{args.runs} 완료")
            if not args.mock and i < args.runs - 1:
                time.sleep(args.pause)

        per_sentence = {}
        agree_sum = 0
        for sid, ls in labels.items():
            if not ls:
                per_sentence[sid] = {"mode": None, "agreement": 0.0, "labels": ls}
                continue
            mode, cnt = Counter(ls).most_common(1)[0]
            agree_sum += cnt
            per_sentence[sid] = {"mode": mode, "agreement": round(cnt / args.runs, 2), "labels": ls}
        rate = agree_sum / (len(labels) * args.runs)
        ranges = {pid: {k: [min(v), max(v)] for k, v in d.items()} for pid, d in para.items()}

        report["files"][f] = {"label_agreement": round(rate, 3), "sentences": per_sentence, "paragraph_ranges": ranges}
        print(f"  라벨 일치율 {rate:.0%} (잠정 목표 80%)")
        low = [sid for sid, v in per_sentence.items() if v["agreement"] < 0.6]
        if low:
            print(f"  흔들리는 문장: {', '.join(low)}")

    out = ROOT / "data" / "runs" / f"consistency_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
