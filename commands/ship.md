# /ship — 커밋 + 푸시 + CI 추적 + 자동 수정 루프

변경사항을 커밋하고 푸시한 뒤, CI 완료까지 추적한다.
CI 실패 시 원인을 분석하고 자동 수정 → 재푸시 → 재추적을 반복한다.

> **검증 게이트**: `verification-before-completion` 스킬의 Iron Law 적용. Step 1 사전 검증 / Step 5 CI GREEN 선언 / Step 6 수정 후 재검증 모두 *이번 ship 호출 안에서* fresh 하게 돌린 출력으로만 PASS 라고 말한다.
> **CI 실패 디버깅**: Step 6 의 "원인 분류" 로 직행하기 전에 `systematic-debugging` 스킬의 Phase 1 (Root Cause) → Phase 2 (Pattern) 진행. evidence 가 환경 차이를 가리키면 그 layer 부터 진단.
> **수정 작성**: Step 6 의 코드 수정은 `test-driven-development` 사이클로 진행 (재현 테스트 먼저).

## 인자

- `$ARGUMENTS`: 커밋 메시지 힌트 (선택). 없으면 변경사항 분석 후 자동 생성한다.

## 실행 순서

### Step 1: 사전 검증
`/verify`와 동일한 검증을 먼저 실행한다.
- 실패 시 자동 수정 시도
- 수정 불가능한 실패가 있으면 중단하고 사용자에게 보고

### Step 2: 스테이징
- `git status`로 변경 파일 확인
- 임시 파일, 로그 파일, .env 등 제외 (tmp*, *.log, backend.log 등)
- 관련 소스 파일만 선별적으로 `git add`
- 스테이징할 파일 목록을 출력하고 확인을 받는다

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
  - 일부 실패 → Step 6 으로

### Step 6: CI 실패 자동 수정 (최대 3회 반복)
- **`systematic-debugging` Phase 1 진입**: evidence 수집을 한 종류만 보지 말고 가능한 만큼 모은다
  - `gh run view {run_id} --log-failed` — 실패 step 로그 (가장 빠른 진단)
  - `gh run view {run_id} --log` — 전체 로그 (실패 직전 컨텍스트 포함)
  - `gh api repos/{owner}/{repo}/actions/runs/{id}/jobs` — job 별 timing, runner OS/arch, matrix leg name 정보 (annotation 은 이 endpoint 에 없음)
  - 각 job 의 annotation 이 필요하면 `gh api repos/{owner}/{repo}/check-runs/{check_run_id}/annotations` (별도 endpoint)
  - artifact 가 있다고 기대되면 `gh run download {run_id}` 시도 — **non-zero exit 시 무시하고 나머지 source 로 계속**. download 실패는 Step 6 의 진행을 막지 않는다
- evidence 가 *어느 layer 에서* 깨지는지 가리킬 때까지 분석 (lint? test? collection? 인프라?)
- 실패 원인 분류 (Phase 1 evidence 기반):
  - **lint/format**: 자동 수정 → 새 커밋 → 재푸시
  - **test 실패**: `test-driven-development` 사이클로 재현 테스트 작성 → 수정 → 새 커밋 → 재푸시
  - **collection/import 에러**: `systematic-debugging` Phase 2 (Pattern) 까지 진행 후 수정
  - **인프라 에러** (Docker, timeout, runner 차이 등): 사용자에게 보고 후 중단
- 수정 후 Step 4 로 돌아가 재푸시 + 재추적 (`verification-before-completion` 게이트 통과 후)
- **3회 반복 후에도 실패 시**: 단순 보고가 아니라 `systematic-debugging` Phase 4.5 (아키텍처 의심) 모드로 사용자에게 에스컬레이션

## 안전장치

- 커밋 전 반드시 파일 목록을 출력하고 승인을 받는다
- force push 절대 금지
- .env, credentials 등 민감 파일 스테이징 차단
- 자동 수정 시 원본 의도를 바꾸는 변경 금지
- 3회 CI 실패 루프 후 자동 중단 → `systematic-debugging` Phase 4.5 보고로 에스컬레이션

## 관련 스킬

- `verification-before-completion` — Step 1, 5, 6 의 PASS 주장은 fresh 출력 필수
- `systematic-debugging` — Step 6 CI 실패 분석 및 3회 fail 시 아키텍처 의심
- `test-driven-development` — Step 6 코드 수정의 회귀 테스트 우선 작성
