# CORTEX V0 · AI 심의위원회

자기소개서가 어떤 인상으로 읽히는지 분석하고, 채용 담당자·기술 전문가·일반 독자 AI가 각자 평가한 뒤 의장 AI가 종합하는 도구입니다.
설계 전체는 `plan.md`를 보세요.

## V0에서 되는 것

```
자기소개서
 → [코드] 문장·문단 분리, ID 부여, 길이·숫자 포함 여부
 → [AI] Analyzer: 문단 역할·기술명(관찰) + 문장별 인상 신호·문단별 점수
 → [AI] 페르소나 3명 독립 평가 + 첫인상 카드 (동시에)
 → [코드] 근거 검증: 원문에 없는 근거는 제외하고 기록
 → [AI] 의장 종합
 → data/runs/실행ID.json
```
실행 1회당 AI 호출 6번. 토론·비교 실험·화면은 V1에서 붙입니다.

## 처음 설정 (Windows, 한 번만)

PowerShell을 열고 이 폴더로 이동합니다.

```powershell
cd D:\Aleph\cortex
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```

메모장이 열리면 `GEMINI_API_KEY=` 뒤에 발급받은 키를 붙여넣고 저장합니다.
`.env` 파일은 다른 사람과 공유하거나 GitHub에 올리지 마세요. (`.gitignore`에 이미 제외되어 있습니다.)

> PowerShell에서 `activate`가 막히면 한 번만 실행: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## 실행

```powershell
# 1) API 없이 흐름만 시험 (가짜 응답)
python -m app.main --file data\inputs\sample_01.txt --mock

# 2) 실제 Gemini로 실행
python -m app.main --file data\inputs\sample_01.txt

# 3) 인상 라벨 일관성 테스트 (같은 글을 5번 분석)
python -m scripts.consistency_check data\inputs\sample_01.txt --runs 5

# 4) 결과 화면 다시 만들기 (AI 호출 없음)
python -m app.report                                        # 가장 최근 결과
python -m app.report data\runs\20260930_103907_001.json     # 특정 결과
python -m app.report --demo data\runs\20260930_103907_001.json   # 사이트용 데모 (demo\index.html)

# 5) 샘플의 객관 항목 확인 (숫자·긴 문장·상투어 등, AI 호출 없음)
python -m scripts.objective_check

# 6) 실행 결과 자동 채점 (정답지 적중률·체크리스트, AI 호출 없음)
python -m scripts.grade
```

실행이 끝나면 `data\reports\실행ID.html` 결과 화면이 자동으로 만들어집니다. 파일 탐색기에서 더블클릭하면 브라우저로 열립니다.

다음에 실행할 때는 `cd D:\Aleph\cortex` → `.venv\Scripts\activate` 만 하면 됩니다.

## 샘플 자기소개서 (10개)

모두 지어낸 글입니다. 무료 티어에 보낸 내용은 Google 제품 개선에 쓰일 수 있으니 **실제 개인정보가 담긴 글은 넣지 마세요.**

| 파일 | 특징 |
|---|---|
| sample_01 | 잘 쓴 글: 문제→해결→수치 결과가 분명함 (백엔드) |
| sample_02 | 상투어가 많고 변명조 (직무 불명) |
| sample_03 | 기술만 나열, 본인 역할과 결과 없음 (인프라) |
| sample_04 | 경험은 많지만 결과가 없음 (프론트엔드) |
| sample_05 | 결과 수치는 있지만 과정이 없음 (데이터) |
| sample_06 | 감정 표현이 강함 (모바일) |
| sample_07 | 지나치게 겸손함 (QA) |
| sample_08 | 문장이 장황함 (인프라) |
| sample_09 | 짧고 간결함 (백엔드) |
| sample_10 | 장점과 약점이 섞임 (풀스택) |

- `data/inputs/samples.md`: 샘플마다 평가자가 짚어야 할 점을 적은 **채점용 정답지**. AI에게 보내지 않습니다. 항목마다 [객관]/[주관]과 근거 출처가 표시돼 있고, 샘플과 정답지 모두 AI가 작성했다는 한계를 적어 두었습니다.
- `data/inputs/review_sheet.md`: 사람에게 샘플 4편을 보여주고 의견을 받는 **블라인드 질문지**. 정답지 없이 이 파일만 전달하세요.

## 폴더 구조

```
app/
  main.py            CLI
  pipeline.py        전체 흐름
  preprocess.py      문장·문단 분리 (코드)
  schemas.py         데이터 구조
  personas.yaml      페르소나 정의 (추가·수정은 여기서)
  prompts/           프롬프트 (코드를 건드리지 않고 실험 가능)
  agents/            analyzer / impression / persona / judge
  utils/             llm(모델 교체는 여기만), validate(근거 검증), logger
scripts/
  consistency_check.py
data/
  inputs/            입력 자기소개서
  runs/              실행 결과 JSON
```

## 로컬 AI(Ollama)로 실행하기

Gemini 무료 한도 없이 내 컴퓨터에서 돌립니다. 그래픽카드가 있는 컴퓨터(예: RTX 4080)에서 빠르고, 내장 그래픽만 있으면 매우 느립니다.

1. [ollama.com/download](https://ollama.com/download)에서 설치하고 모델을 받습니다 (예: `ollama pull qwen3.5:9b`)
2. 터미널에서 `ollama list`로 모델 이름을 확인합니다
3. `.env`에 두 줄을 적습니다
   ```
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=ollama list에 나온 이름
   ```
4. 평소처럼 실행합니다: `python -m app.main --file data\inputs\sample_01.txt`

결과 파일의 모델 이름은 `ollama/모델이름`으로 기록됩니다. **Gemini 결과와 로컬 결과를 섞어서 비교하지 마세요.**

## 알아둘 것

- **429 오류**: 무료 티어의 분당 한도에 걸린 것입니다. 자동으로 기다렸다 재시도합니다. 계속 걸리면 `.env`의 모델을 `gemini-3.5-flash-lite`로 바꿔보세요.
- **모델 교체**: `.env`의 `GEMINI_MODEL` 또는 `--model` 옵션. 다른 회사 모델로 바꾸려면 `app/utils/llm.py`만 수정합니다.
- **프롬프트를 바꾸면** 결과 JSON의 `metadata.prompt_hashes`가 달라져서 어떤 버전으로 실행했는지 추적됩니다.
- **인상 분석은 진단이 아닙니다.** "이 글이 이렇게 읽힌다"는 언어적 신호일 뿐, 작성자의 성격이나 상태를 판단하지 않습니다.
