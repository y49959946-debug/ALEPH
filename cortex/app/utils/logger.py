"""실행 로그(run.json) 저장과 프롬프트 해시."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
PROMPT_DIR = APP_DIR / "prompts"


def prompt_hashes() -> dict[str, str]:
    """어떤 프롬프트 버전으로 실행했는지 기록한다 (앞 12자리)."""
    files = sorted(PROMPT_DIR.glob("*.txt")) + [APP_DIR / "personas.yaml"]
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest()[:12] for f in files if f.exists()}


def new_run_id(runs_dir: Path) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    n = len(list(runs_dir.glob(f"{stamp}_*.json"))) + 1
    return f"{stamp}_{n:03d}"


def save_run(run: dict, runs_dir: Path) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{run['run_id']}.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
