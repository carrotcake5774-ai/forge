# /ship — 커밋 + 푸시 + CI 추적 + 자동 수정 루프

변경사항을 커밋하고 푸시한 뒤, CI 완료까지 추적합니다.
CI 실패 시 원인을 분석하고 자동 수정 → 재푸시 → 재추적을 반복합니다.

## 인자

- `$ARGUMENTS`: 커밋 메시지 힌트 (선택). 없으면 변경사항 분석 후 자동 생성.

## 실행 순서

### Step 1: 사전 검증
`/verify`와 동일한 검증을 먼저 실행.
- 실패 시 자동 수정 시도
- 수정 불가능한 실패가 있으면 중단하고 사용자에게 보고

### Step 2: 스테이징
- `git status`로 변경 파일 확인
- 임시 파일, 로그 파일, .env 등 제외 (tmp*, *.log, backend.log 등)
- 관련 소스 파일만 선별적으로 `git add`
- 스테이징할 파일 목록을 사용자에게 보여주고 확인 요청

### Step 3: 커밋
- `git diff --cached --stat`와 `git log --oneline -3`을 분석
- 프로젝트 커밋 메시지 컨벤션(한국어/영어, "why" 중심)에 맞는 메시지 작성
- `$ARGUMENTS`가 있으면 힌트로 활용
- `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>` 포함
- HEREDOC 형식으로 커밋

### Step 4: 푸시
- `git push` 실행

### Step 5: CI 추적
- `gh run list --limit 1`로 CI run ID 확인
- `gh run watch {run_id}`로 완료까지 추적
- 완료 시 결과 요약:
  - 모든 job 통과 → "CI 전체 GREEN" 출력
  - 일부 실패 → Step 6으로

### Step 6: CI 실패 자동 수정 (최대 3회 반복)
- `gh run view {run_id} --log-failed`로 실패 로그 분석
- 실패 원인 분류:
  - **lint/format**: 자동 수정 → 새 커밋 → 재푸시
  - **test 실패**: 원인 분석 → 코드 수정 → 새 커밋 → 재푸시
  - **인프라 에러** (Docker, timeout 등): 사용자에게 보고 후 중단
- 수정 후 Step 4로 돌아가 재푸시 + 재추적
- 3회 반복 후에도 실패 시 사용자에게 보고

## 안전장치

- 커밋 전 반드시 파일 목록을 사용자에게 보여주고 확인
- force push 절대 금지
- .env, credentials 등 민감 파일 스테이징 차단
- 자동 수정 시 원본 의도를 바꾸는 변경 금지
- 3회 CI 실패 루프 후 자동 중단
