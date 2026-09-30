"""샘플의 객관 항목(O1~O6) 확인 (AI 호출 없음).

정답지(data/inputs/samples.md)의 [객관] 표시는 이 스크립트 결과를 기준으로 한다.
목록 일치는 "그 표현이 쓰였다"는 사실만 알려줄 뿐, 그게 문제인지는 판단하지 않는다.

사용법 (프로젝트 폴더에서):
    python -m scripts.objective_check                 # 모든 샘플
    python -m scripts.objective_check data\\inputs\\sample_06.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.preprocess import preprocess  # noqa: E402

LONG = 150
LISTS = {
    "O3 상투어": ["열정적", "혁신적", "창의적", "다양한", "최선을 다", "책임감", "성장하는", "인재"],
    "O4 변명·남 탓": ["때문이었", "어떻게 할 수 있는 부분은 아니", "촉박했"],
    "O5 자기 축소": ["부족한", "운이 좋았", "조금", "특별히 잘해서라기보다"],
    "O6 감정 표현": ["가슴을 뛰게", "행복했", "부둥켜안", "뜨거운 열정", "떨림"],
}


def check(path: Path) -> None:
    pre = preprocess(path.read_text(encoding="utf-8"))
    ss = pre.sentences
    print(f"\n{path.name}  (문단 {len(pre.paragraphs)}, 문장 {len(ss)}, 글자 {sum(s.length for s in ss)})")
    print(f"  O1 숫자 포함      {[s.id for s in ss if s.has_number] or '-'}")
    print(f"  O2 {LONG}자 초과     {[s.id + f'({s.length})' for s in ss if s.length > LONG] or '-'}")
    for name, words in LISTS.items():
        hits = [f"{s.id}:{w}" for s in ss for w in words if w in s.text]
        print(f"  {name:<12} {hits or '-'}")


def main() -> int:
    files = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "data" / "inputs").glob("sample_*.txt"))
    for f in files:
        check(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
