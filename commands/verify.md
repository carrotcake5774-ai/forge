# /verify — 전체 검증 파이프라인

모든 검증 단계를 순차 실행하고, 실패 시 자동 수정을 시도한다.

> **게이트 스킬**: 이 명령은 `verification-before-completion` 스킬의 Iron Law 를 따른다.
> 각 단계의 PASS 는 *이번 호출에서 fresh 하게* 돌린 출력으로만 입증되며, 이전 실행/캐시 인용은 금지.
> **디버깅 스킬**: 단계 실패 시 단순 자동수정으로 떨어지기 전에 `systematic-debugging` 스킬의 Phase 1 (Root Cause) 을 적용. ruff `--fix` 같은 단순 케이스만 우회 허용.

## 인자

- `$ARGUMENTS`: 검증 옵션
  - `--full`: performance 마커 테스트도 포함하여 실행 (기본은 `-m "not performance"`)

## 실행 순서

1. **ruff check** (`uv run ruff check packages/ backend/ cli/`)
   - 실패 시: ruff `--fix` 가 자동 수정 가능한 단순 케이스(unused import 등)는 즉시 `--fix` 적용 후 재검사. **이건 systematic-debugging 우회가 허용된 유일한 단순 케이스.**
   - `--fix` 후에도 실패가 남으면: `systematic-debugging` Phase 1 (Root Cause) 진행 후 수동 수정 항목 목록 출력

2. **ruff format** (`uv run ruff format packages/ backend/ cli/ --check`)
   - 실패 시: `uv run ruff format packages/ backend/ cli/` 자동 적용

3. **next build** (`cd frontend && npx next build`)
   - 실패 시: 에러 메시지 분석 후 TypeScript 에러 수정 시도
   - 수정 후 재빌드

4. **Docker DB 기동 확인** (`make db-up` 또는 `docker compose up -d`)
   - PostgreSQL + Redis 컨테이너 실행 상태 확인
   - 미기동 시 자동 시작 → **고정 sleep 금지**, `pg_isready` 폴링으로 readiness 확인:
     ```bash
     # 서비스 이름은 docker compose ps 에서 동적 탐지 (forge 는 범용 플러그인)
     PG_SVC=$(docker compose ps --services 2>/dev/null | grep -E '^(postgres|postgresql|pg|db|database)$' | head -1)
     REDIS_SVC=$(docker compose ps --services 2>/dev/null | grep -E '^(redis|cache)$' | head -1)
     [ -n "$PG_SVC" ] && timeout 30 bash -c "until docker compose exec -T $PG_SVC pg_isready -q; do sleep 0.5; done"
     [ -n "$REDIS_SVC" ] && timeout 10 bash -c "until docker compose exec -T $REDIS_SVC redis-cli ping >/dev/null 2>&1; do sleep 0.5; done"
     ```
   - 서비스 이름이 위 패턴에 안 맞으면 `FORGE_PG_SERVICE` / `FORGE_REDIS_SERVICE` 환경변수로 override
   - process 가 running 이어도 service 는 아직 connection 못 받을 수 있음 (3초 sleep 은 거짓 readiness)
   - **push 전 반드시 실제 DB 에서 테스트를 돌려야 CI 실패를 예방함**

5. **pytest** (`uv run pytest -m "not performance" -q`, `--full` 모드는 `uv run pytest -q`)
   - 성능 테스트 제외하고 실행 (기본). `--full` 인자가 있으면 성능 테스트 포함
   - **실제 PostgreSQL 연결 필수** (mock 금지, CLAUDE.md 규칙)
   - **exit code capture 필수**: pytest 실행 직후 `EC=$?` 로 exit code 를 보존하고 아래 분기 적용 (출력 텍스트만으로 판정 금지 — collection error 가 test fail 과 혼동됨)
   - **exit code 분기**:
     - `0` → PASS
     - `1` → 테스트 실패. 실패한 테스트와 에러 메시지 출력
     - `2` → collection/사용 에러 (import 실패 등). PASS 도 FAIL 도 아닌 *블로커*. `systematic-debugging` Phase 1 진행
     - `5` → 수집된 테스트 0개. 변경된 파일에 대응하는 test 디렉토리가 있는데 0 이면 사용자 보고. test 디렉토리가 애초에 없는 작업 (frontend-only, 초기 phase) 이면 warning 으로 격하
     - 기타 → 인프라 에러 (DB down, OOM 등). 사용자 보고

## 출력 형식

각 단계 완료 시 결과를 한 줄로 요약:
```
[1/5] ruff check    — PASS
[2/5] ruff format   — PASS (1 file reformatted)
[3/5] next build    — PASS (35 pages)
[4/5] docker db     — PASS (PostgreSQL + Redis running)
[5/5] pytest        — PASS (790 passed, 0 failed)
```

실패한 단계가 있으면 자동 수정을 시도하고, 수정 후 해당 단계만 재실행.
최종적으로 전체 PASS/FAIL 요약 출력.

## 자동 수정 범위

- ruff lint: `--fix`로 자동 수정 가능한 것만
- ruff format: 자동 포맷 적용
- TypeScript: import 누락, 타입 에러 등 명확한 것만
- pytest 실패: 수정하지 않음 (원인 분석만 출력)

## 주의

- 자동 수정된 파일은 목록으로 출력하여 확인 가능하게 한다
- 원본 코드의 의도를 바꾸는 수정은 절대 하지 않는다

## 관련 스킬

- `verification-before-completion` — "fresh evidence 없이 PASS 라고 말하지 않는다" 게이트
- `systematic-debugging` — fail 단계의 Root Cause 분석 (Phase 1 → 4)
- `test-driven-development` — fix 작성 시 RED-GREEN-REFACTOR 사이클 강제
