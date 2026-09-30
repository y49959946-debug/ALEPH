"""내 컴퓨터에서 여는 CORTEX 화면 (로컬 전용).

공개 사이트와 같은 화면(글 넣기 → 심의 → 결과)을 띄우고, 글 넣기에서 실제로 분석을 돌린다.
내 컴퓨터(127.0.0.1)에서만 열리고, 같은 와이파이의 다른 기기에서는 접속할 수 없다.

사용법 (프로젝트 폴더에서):
    python -m app.server            # .env 설정대로 (Gemini 또는 Ollama)
    python -m app.server --mock     # AI 없이 가짜 응답으로 화면만 시험
그다음 브라우저에서 http://localhost:8765 를 연다.

한 번에 분석 하나만 돌린다 (무료 한도와 로컬 AI 메모리를 지키기 위해).
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from . import web  # noqa: E402
from .pipeline import run_pipeline  # noqa: E402
from .utils.llm import LLMError, make_client  # noqa: E402

MAX_CHARS = 3000
MIN_CHARS = 50
JOBS: dict[str, dict] = {}
BUSY = threading.Lock()
OPTS = {"mock": False, "model": None}


def _page() -> str:
    """요청마다 새로 만든다. 방금 끝난 분석도 바로 보이도록."""
    runs = web.all_runs()
    chosen = {r["run_id"]: r for r in runs}
    chosen.update(web.latest_per_sample(runs))
    return web.build_page(chosen, local=True)


def _worker(job_id: str, text: str, source: str) -> None:
    job = JOBS[job_id]
    try:
        client = make_client(mock=OPTS["mock"], model=OPTS["model"])
        run, _ = run_pipeline(text, client, web.RUNS_DIR, source=source, log=job["logs"].append)
        job.update(status="done", run_id=run["run_id"])
    except LLMError as e:
        job.update(status="error", error=str(e))
    except Exception as e:  # 화면에 원인을 보여주고 서버는 계속 켜 둔다
        job.update(status="error", error=f"{type(e).__name__}: {e}")
    finally:
        BUSY.release()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # 요청마다 찍히는 로그는 끈다
        pass

    def _send(self, code: int, body: str | bytes, ctype: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code: int, obj: dict) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/view.html"):
            return self._send(200, _page())
        if path.startswith("/api/run/"):
            rid = path.rsplit("/", 1)[-1]
            f = web.RUNS_DIR / f"{rid}.json"
            if not rid.replace("_", "").isdigit() or not f.exists():
                return self._json(404, {"error": "없는 결과예요"})
            return self._json(200, web.slim(json.loads(f.read_text(encoding="utf-8"))))
        if path == "/api/health":
            import os
            provider = "mock" if OPTS["mock"] else os.getenv("LLM_PROVIDER", "gemini").strip().lower()
            try:
                model = make_client(mock=OPTS["mock"], model=OPTS["model"]).model_name
            except LLMError as e:
                model = f"설정 오류: {e}"
            return self._json(200, {"provider": provider, "model": model, "busy": BUSY.locked()})
        if path.startswith("/api/job/"):
            job = JOBS.get(path.rsplit("/", 1)[-1])
            if not job:
                return self._json(404, {"error": "없는 작업이에요"})
            return self._json(200, {k: job.get(k) for k in ("status", "logs", "run_id", "error")})
        return self._send(404, "없는 페이지예요")

    def do_POST(self):
        if urlparse(self.path).path != "/api/analyze":
            return self._json(404, {"error": "없는 주소예요"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(min(length, 200_000)).decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "요청을 읽지 못했어요"})
        text = str(body.get("text", "")).strip()
        source = str(body.get("source", ""))
        if not (MIN_CHARS <= len(text) <= MAX_CHARS):
            return self._json(400, {"error": f"{MIN_CHARS}~{MAX_CHARS}자 사이로 넣어 주세요"})
        # 샘플 경로만 source로 인정한다 (사이트 데모에는 샘플 결과만 들어가므로)
        if source and not (source.startswith("data/inputs/sample_") and source.endswith(".txt")):
            source = ""
        if not BUSY.acquire(blocking=False):
            return self._json(409, {"error": "이미 분석이 진행 중이에요. 끝난 뒤 다시 시도해 주세요"})
        job_id = uuid.uuid4().hex[:12]
        JOBS[job_id] = {"status": "running", "logs": [], "run_id": None, "error": None}
        threading.Thread(target=_worker, args=(job_id, text, source), daemon=True).start()
        print(f"분석 시작 ({len(text)}자){' · ' + source if source else ''}")
        return self._json(202, {"job": job_id})


def main() -> int:
    parser = argparse.ArgumentParser(description="CORTEX 로컬 화면")
    parser.add_argument("--mock", action="store_true", help="AI 없이 가짜 응답으로 시험")
    parser.add_argument("--model", help="모델 이름 (기본: .env 설정)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="브라우저를 자동으로 열지 않음")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    OPTS.update(mock=args.mock, model=args.model)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"CORTEX 로컬 화면: {url}  (끄려면 Ctrl+C)")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
