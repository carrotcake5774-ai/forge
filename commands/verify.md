# /verify — 전체 검증 파이프라인

모든 검증 단계를 순차 실행하고, 실패 시 자동 수정을 시도합니다.

## 실행 순서

1. **ruff check** (`uv run ruff check packages/ backend/ cli/`)
   - 실패 시: `--fix` 자동 적용 후 재검사
   - 그래도 실패 시: 수동 수정이 필요한 항목 목록 출력

2. **ruff format** (`uv run ruff format packages/ backend/ cli/ --check`)
   - 실패 시: `uv run ruff format packages/ backend/ cli/` 자동 적용

3. **next build** (`cd frontend && npx next build`)
   - 실패 시: 에러 메시지 분석 후 TypeScript 에러 수정 시도
   - 수정 후 재빌드

4. **Docker DB 기동 확인** (`make db-up` 또는 `docker compose up -d`)
   - PostgreSQL + Redis 컨테이너 실행 상태 확인
   - 미기동 시 자동 시작 후 3초 대기
   - **push 전 반드시 실제 DB에서 테스트를 돌려야 CI 실패를 예방함**

5. **pytest** (`uv run pytest -m "not performance" -q`)
   - 성능 테스트 제외하고 실행
   - **실제 PostgreSQL 연결 필수** (mock 금지, CLAUDE.md 규칙)
   - 실패 시: 실패한 테스트와 에러 메시지 출력
   - `$ARGUMENTS`에 `--full`이 포함되면 성능 테스트도 포함

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
