---
name: verification-before-completion
description: "PASS/완료/성공을 주장하기 *직전* 에 반드시 fresh 검증 명령을 돌리고 출력으로 입증하도록 강제하는 게이트 스킬. /verify 5단계 결과 보고, /ship Step 1·5·6, 단일 작업 완료 보고 직전에 호출. 트리거: '다 끝났어요', '완료했습니다', '통과 확인', 'PASS 보고', '커밋 직전', 'ship 직전'"
effort: medium
---

# Verification Before Completion

> **호출**: forge의 모든 "완료" 시점 (`/verify`, `/ship`, `/execute-plan` 태스크 종결, 다음 wave 진입 직전)
> **목적**: "되어 있을 거다"가 아니라 "방금 돌려서 OK였다"만 신뢰
> **출처**: superpowers/verification-before-completion 철학을 forge 톤으로 흡수

---

## 핵심 원칙

**검증 없는 완료 주장은 효율이 아니라 거짓말이다.**

증거가 먼저, 주장은 그 다음.

> 규칙의 자구를 어기는 것은 규칙의 정신을 어기는 것이다.

---

## Iron Law

```
이번 메시지에서 직접 검증 명령을 돌리지 않았다면, PASS 라고 말할 수 없다.
```

- 이전 실행 결과? 무효
- 캐시된 출력? 무효
- "아마 통과할 것이다"? 거짓말
- "lint 가 통과했으니 build 도 될 것이다"? 거짓말

---

## Gate Function (forge 파이프라인 적용)

완료/성공/만족 표현을 내뱉기 *직전*에 다음 절차를 거친다.

```
1. IDENTIFY  — 이 주장을 입증하는 명령은 정확히 무엇인가?
2. RUN       — 그 명령을 fresh 하게, 전체로 실행
3. READ      — 전체 출력 + exit code + 실패 카운트 확인
4. VERIFY    — 출력이 주장을 입증하는가?
                NO  -> 실제 상태를 출력과 함께 보고
                YES -> 출력 증거를 첨부하여 주장
5. THEN      — 그제서야 PASS 라 말한다
```

한 단계라도 건너뛰면 검증이 아니라 거짓말이다.

---

## forge에서 PASS를 입증하는 기본 명령

| 주장 | 입증 명령 (forge 표준 스택) | 충분 조건 |
|------|---------------------------|----------|
| "lint clean" | `uv run ruff check packages/ backend/ cli/` | exit 0, 0 errors |
| "format clean" | `uv run ruff format ... --check` | exit 0 |
| "build OK" | `cd frontend && npx next build` | exit 0, 모든 page 빌드 |
| "tests pass" (기본) | `uv run pytest -m "not performance" -q` | 0 failed, **실제 PostgreSQL 연결**, mock 금지 |
| "tests pass" (`--full` 모드) | `uv run pytest -q` (performance 포함) | 0 failed, 실제 DB, mock 금지 — `--full` 인자 시 이걸로 입증해야 함 |
| "DB up" | `docker compose ps` | postgres + redis 둘 다 running |
| "버그 수정됨" | 원래 증상을 재현하는 테스트 작성 → RED → 수정 → GREEN | RED-GREEN 둘 다 직접 본 것 |
| "agent 가 끝냈다" | `git diff` / `git status` | 코드 차이가 실제로 보임. agent 의 "success" 보고만으로는 NO |
| "요구사항 충족" | 플랜 문서 라인별 체크리스트 | 항목별 ✓ 표시 + 미충족 항목 명시 |

> **forge 고유 규칙**: "mock으로 통과했다"는 NEVER 충분 조건이 아니다. CLAUDE.md 규칙대로 실제 PostgreSQL에서 돌아간 결과만 인정.

---

## Red Flags — STOP

다음 표현/상황이 떠오르면 그 즉시 검증 단계로 복귀.

- "should", "probably", "seems to", "아마", "될 거예요", "거의 다 됐어요"
- 검증 *전*에 "Great!", "Done!", "완료!", "🎉" 같은 만족 표현
- `/ship` 진입 직전인데 `/verify` 결과를 *이번 메시지*에서 확인하지 않은 상태
- 서브에이전트(Task)가 "성공" 보고했고 git diff를 보지 않은 상태
- 일부 단계만 돌리고 나머지는 건너뛴 상태
- "이번 한 번만"이라는 생각
- 피곤해서 빨리 끝내고 싶은 상태
- **검증을 안 했음에도 성공을 시사하는 어떤 표현이든**

---

## Rationalization Prevention

| 변명 | 현실 |
|------|------|
| "이제 될 거예요" | 검증 명령을 직접 돌려라 |
| "확신해요" | 확신 ≠ 증거 |
| "이번 한 번만" | 예외 없음 |
| "linter 통과했어요" | linter ≠ compiler ≠ test runner |
| "agent 가 성공했다고 보고함" | git diff 로 독립 검증 |
| "피곤해요" | 피로 ≠ 면제 사유 |
| "부분 검증으로 충분해요" | 부분 검증은 아무것도 입증하지 않는다 |
| "단어를 바꿨으니 규칙 적용 안 됨" | spirit > letter |
| "이전 실행에서 통과했음" | 이번 메시지에서 다시 돌려라 |

---

## forge 파이프라인 적용 지점

본 스킬의 일차 가치는 *단일 작업자가 어떤 결과를 보고하기 직전* 의 게이트에 있다. 호출 위치를 우선순위 순으로:

| 시점 | 무엇을 강제하는가 |
|------|------------------|
| **`/verify` — 각 단계 결과 출력 직전** | 5단계 모두 *이번 호출에서* fresh 실행 (이전 캐시/로그 인용 금지) |
| **`/ship` — Step 1 사전 검증** | `/verify` 전체를 *이 ship 호출 안에서* 새로 한 번 더 |
| **`/ship` — CI 추적 종료 후 GREEN 선언 직전** | `gh run view` 로 현재 run 의 conclusion 직접 재확인 |
| **`/ship` — Step 6 수정 후 재푸시 직전** | 수정 사항이 실제로 회귀를 잡는지 fresh fix-and-rerun 으로 입증 |
| **단일 작업 완료 보고 직전** | "이 작업 다 됐어요" 라는 발화 직전, 입증 명령을 이번 메시지에서 직접 돌려 출력 첨부 |
| 서브에이전트 위임 후 결과 수신 시 | 보고를 신뢰하지 말고 git diff + 변경 파일 Read 로 독립 검증 |

## STAGE 9 와의 관계

STAGE 9-3 / 9-4 의 step 5/6/7/8 은 이미 자체적으로 fresh 측정과 비교를 수행한다 (`pipeline.md` 9-4 의 loop 정의 참조). 본 스킬은 그 절차를 *다른 이름으로 부를 뿐* 새 행동을 만들지 않는다. STAGE 9 의 진짜 게이트는 forge 자체의 출제자/응시자 분리 + git rollback 이고, 본 스킬은 그 절차의 원리적 안내일 뿐이다.

## STAGE 8 (`/execute-plan`) 와의 관계

STAGE 8 에는 본 게이트가 호출되지 않는다. STAGE 8 은 의도적으로 가벼운 lint 만 하고, 모든 검증 책임은 §5 의 `/verify` 와 STAGE 9 가 진다.

---

## 재현 테스트 (RED-GREEN) 입증 규칙

버그 수정의 경우 단순히 "테스트가 통과한다"로는 부족하다.

```
1. 버그를 재현하는 실패 테스트 작성 (RED)
2. 그대로 돌려서 FAIL 확인     <- 직접 보지 않으면 무효
3. 수정 사항 적용
4. 돌려서 PASS 확인 (GREEN)
5. 수정을 잠시 revert
6. 돌려서 다시 FAIL 확인        <- 테스트가 정말 그 버그를 잡는지 입증
7. 수정 복원, PASS 확인
```

3-7 절차를 *직접* 실행하지 않은 재현 테스트는 재현 테스트가 아니다.

> 용어: forge 에서 "재현 테스트" 는 *특정 버그를 재현하는* 테스트, "영향 영역 회귀" 는 *변경 주변의 기존 동작이 깨지지 않았는지* 확인하는 회귀 검사. 둘은 다른 개념.

---

## Bottom Line

검증에는 지름길이 없다.

명령을 돌리고, 출력을 읽고, **그 다음에** 결과를 말한다.

이 규칙은 협상 불가다.

---

## 관련 스킬

- `test-driven-development` — RED-GREEN 사이클의 각 단계가 본 스킬의 게이트를 통과해야 함
- `systematic-debugging` — Phase 4 의 fix 검증이 본 스킬의 게이트를 통과해야 함
- `commands/verify.md` — 본 스킬을 호출하는 5단계 검증 명령
- `commands/ship.md` — Step 1, 5, 6 모두 본 스킬의 fresh-evidence 게이트 적용
