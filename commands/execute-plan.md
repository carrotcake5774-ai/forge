# /execute-plan — 태스크 기반 자동 실행

TaskList의 pending 태스크를 의존성 순서대로 실행합니다.
각 태스크 완료 후 중간 검증을 수행하고, 전체 완료 시 `/verify`를 실행합니다.

## 인자

- `$ARGUMENTS`: 실행 옵션
  - `--dry-run`: 실행 계획만 출력하고 실제 실행하지 않음
  - `--phase N`: 특정 Phase 태스크만 실행
  - `--parallel`: 의존성 없는 태스크를 Agent로 병렬 실행 (기본값)
  - `--sequential`: 모든 태스크를 순차 실행

## 실행 로직

### 1. 태스크 분석
- TaskList에서 pending 태스크 수집
- blockedBy 의존성으로 실행 순서(wave) 결정:
  - Wave 1: 의존성 없는 태스크 (동시 실행 가능)
  - Wave 2: Wave 1에 의존하는 태스크
  - ...

### 2. Wave 실행
각 wave 내에서:
- **독립 태스크 2개 이상**: Agent로 병렬 실행 (sonnet 모델)
  - 각 에이전트에게 태스크 description + 대상 파일 목록 + CLAUDE.md 규칙 전달
  - 서로 다른 파일을 수정하는 경우만 병렬 허용
  - 같은 파일을 수정하는 태스크는 순차 실행
- **독립 태스크 1개**: 직접 실행

### 3. 태스크별 처리
각 태스크 실행 시:
1. TaskUpdate → `in_progress`
2. 대상 파일 읽기
3. 코드 변경 구현
4. 변경 후 관련 lint 체크 (`ruff check` on changed files)
5. TaskUpdate → `completed`

### 4. Wave 간 중간 검증
wave 완료 후:
- `ruff check` + `ruff format --check` (변경된 파일만)
- 실패 시 자동 수정 후 계속

### 5. 전체 완료 검증
모든 태스크 완료 후:
- `/verify` 전체 실행
- 결과 요약 출력

## 안전장치

- 각 wave 시작 전 실행할 태스크 목록을 사용자에게 표시
- 에이전트 실행 결과에 충돌(같은 파일 수정)이 있으면 수동 머지 요청
- 3회 연속 같은 태스크에서 실패하면 해당 태스크 건너뛰고 사용자에게 보고
- `--dry-run`으로 먼저 실행 계획 확인 가능

## 출력 형식

```
=== Wave 1 (3 tasks, parallel) ===
  [1/3] Phase 0-1: 누계합계 수정 ............ DONE (2 files changed)
  [2/3] Phase 0-2: 역분개 날짜 .............. DONE (1 file changed)
  [3/3] Phase 0-3: CLI BOM .................. DONE (1 file changed)
  Mid-check: ruff ✓ | format ✓

=== Wave 2 (2 tasks, parallel) ===
  [4/5] Phase A-1: date_field ............... DONE (3 files changed)
  [5/5] Phase A-2: Inbox .................... DONE (4 files changed)
  Mid-check: ruff ✓ | format ✓

=== Final Verification ===
  ruff check ........ PASS
  ruff format ....... PASS
  next build ........ PASS
  pytest ............ PASS (790/790)

All 5 tasks completed. Ready to /ship.
```
