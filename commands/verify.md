# /verify — 전체 검증 파이프라인

모든 검증 단계를 순차 실행하고, 실패 시 자동 수정을 시도합니다.

## 인자

- `$ARGUMENTS`: 검증 옵션
  - `--full`: performance 마커 테스트도 포함하여 실행 (기본은 `-m "not performance"`)

## 실행 순서

1. **ruff check** (`uv run ruff check packages/ backend/ cli/`)
   - 실패 시: `--fix` 자동 적용 후 재검사
   - 그래도 실패 시: 수동 수정이 필요한 항목 목록 출력

2. **ruff format** (`uv run ruff format packages/ backend/ cli/ --check`)
   - 실패 시: `uv run ruff format packages/ backend/ cli/` 자동 적용

3. **next build** (`cd frontend && npx next build`)
   - 실패 시: 에러 메시지 분석 후 TypeScript 에러 수정 시도
   - 수정 후 재빌드

4. **Docker DB readiness 확인** (`make db-up` 또는 `docker compose up -d`)
   - PostgreSQL + Redis 컨테이너 실행 상태 확인
   - 미기동 시 자동 시작 → **고정 sleep 금지**, `pg_isready` + `redis-cli ping` 폴링으로 readiness 확인:
     ```bash
     timeout 30 bash -c 'until docker compose exec -T postgres pg_isready -q; do sleep 0.5; done'
     timeout 10 bash -c 'until docker compose exec -T redis redis-cli ping >/dev/null 2>&1; do sleep 0.5; done'
     ```
   - 서비스 이름은 `postgres`, `redis` 로 가정 (forge 의 다른 부분과 동일 가정). 다른 이름이면 위 두 줄을 직접 편집
   - process 가 running 이어도 service 는 아직 connection 못 받을 수 있음 — 3초 sleep 으로는 부족
   - **push 전 반드시 실제 DB 에서 테스트를 돌려야 CI 실패를 예방함**

5. **pytest** (`uv run pytest -m "not performance" -q`, `--full` 모드는 `uv run pytest -q`)
   - 성능 테스트 제외하고 실행 (기본). `--full` 인자가 있으면 성능 테스트 포함
   - **실제 PostgreSQL 연결 필수** (mock 금지, CLAUDE.md 규칙)
   - **exit code 분기 — pytest 출력 텍스트만으로 판정 금지.** 다음 snippet 로 실행하여 exit code 를 직접 capture:
     ```bash
     set +e
     uv run pytest -m "not performance" -q
     EC=$?
     set -e
     ```
   - 분기:
     - `EC=0` → PASS
     - `EC=1` → 테스트 실패. 실패한 테스트와 에러 메시지 출력
     - `EC=2` → collection / 사용 에러 (import 실패 등). PASS 도 FAIL 도 아닌 *블로커*. 사용자에게 보고 (출력 텍스트만 보면 "0 failed" 로 보일 수 있으니 EC 우선)
     - `EC=5` → 수집된 테스트 0개. **PASS 로 보고 금지.** 변경된 파일에 대응하는 test 디렉토리가 있는데 0이면 사용자 보고. 작업이 애초에 test-less 영역(frontend-only, 초기 phase) 이면 warning 으로 격하
     - 그 외 → 인프라 에러 (DB down, OOM 등). 사용자 보고

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

- 자동 수정된 파일은 목록으로 출력하여 사용자가 확인할 수 있게 함
- 원본 코드의 의도를 바꾸는 수정은 절대 하지 않음
