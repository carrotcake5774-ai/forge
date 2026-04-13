---
name: systematic-debugging
description: "버그/테스트 실패/예상 외 동작에 대해 추측 fix 대신 4단계(Root Cause → Pattern → Hypothesis → Fix) 프로세스를 강제하는 디버깅 스킬. /verify 단계 실패, /ship Step 6 (CI 실패), /pipeline STAGE 9-4 step 3 (실패/저점 항목 분석), /codex:rescue 진입, 3회 연속 rollback 시 호출. 트리거: '에러 났어', '안 돌아가', '터졌어', '예외', 'exception', 'stack trace', '재현', 'CI 실패', '워크플로우 fail', '저점 카테고리', 'Gold test fail'"
effort: medium
---

# Systematic Debugging

> **호출**: `/verify` 단계 실패, `/ship` Step 6 (CI 실패 자동 수정), `/codex:rescue` 위임, `/pipeline` STAGE 9-4 의 저점 항목 분석, 단일 작업자의 격리된 디버깅
> **방식**: Phase 1 Root Cause → Phase 2 Pattern → Phase 3 Hypothesis → Phase 4 Fix
> **출처**: superpowers/systematic-debugging 철학을 forge 톤으로 흡수

---

## 핵심 원칙

**무작위 수정은 시간을 낭비하고 새 버그를 만든다. 임시방편은 근본 원인을 가린다.**

> 항상 root cause 를 찾고 나서 수정을 시도한다. 증상 봉합은 실패다.

> 규칙의 자구를 어기는 것은 규칙의 정신을 어기는 것이다.

---

## Iron Law

```
Phase 1 (Root Cause) 을 끝내기 전에는 수정을 제안하지 않는다.
```

---

## When to Use

모든 기술적 이슈에 적용:
- 테스트 실패
- production 버그
- 예상 외 동작
- 성능 문제
- 빌드 실패
- CI 실패 (forge `/ship` Step 6)
- 통합 이슈

**특히 다음 상황에서 절대 건너뛰지 말 것:**
- 시간 압박 (응급일수록 추측이 끌리고, 추측이 더 느리다)
- "한 줄만 고치면 될 것 같다" 가 떠오를 때
- 수정을 이미 여러 번 시도했을 때
- 이전 수정이 안 먹혔을 때
- 이슈를 완전히 이해하지 못한 상태

---

## The Four Phases

각 Phase 는 **반드시 순서대로** 완료해야 다음으로 넘어간다.

---

### Phase 1: Root Cause Investigation

**어떤 fix 도 시도하기 전에:**

#### 1.1 에러 메시지를 끝까지 읽는다

- skip 금지. 경고도 skip 금지.
- 종종 정답이 메시지 안에 있다.
- stack trace 전체 읽기.
- 라인 번호, 파일 경로, 에러 코드 모두 기록.

#### 1.2 일관되게 재현

- 매번 트리거 가능한가?
- 정확한 재현 절차는?
- 100% 재현되는가?
- **재현 안 되면 → 데이터를 더 모은다. 추측 금지.**

#### 1.3 최근 변경 확인

- 무엇이 바뀌었는가?
- `git log --oneline -20`, `git diff HEAD~5`
- 새 dependency, 환경 변수, config?
- 환경 차이 (local vs CI vs prod)?

#### 1.4 다층 시스템에서는 layer 별 evidence 수집

forge 시스템 예시: **frontend (Next) → backend (Python) → DB (PostgreSQL) → Docker 환경**

각 layer 경계마다:
- 들어오는 데이터를 로그로 본다
- 나가는 데이터를 로그로 본다
- 환경/설정 전파 확인
- 각 layer 의 상태 확인

**한 번 돌려서 어느 layer 가 깨지는지 evidence 를 모은다 → 그 layer 를 조사한다.**

forge 표준 진단 명령:
```bash
# Layer 0: Docker 환경
docker compose ps
docker compose logs --tail 50 postgres redis

# Layer 1: backend 환경 변수 / DB 연결
uv run python -c "from backend.db import engine; print(engine.url)"

# Layer 2: 실제 쿼리
uv run pytest tests/integration/ -k {keyword} -s -x

# Layer 3: API ↔ frontend
curl -v http://localhost:8000/api/{endpoint}

# Layer 4: frontend 빌드/런타임
cd frontend && npx next build 2>&1 | tee /tmp/next-build.log
```

**이 evidence 가 어느 layer 가 실패하는지 보여준다** (예: DB ✓, backend → frontend ✗).

#### 1.5 데이터 흐름 역추적

깊은 call stack 안에서 에러가 났다면:
- 잘못된 값이 어디서 시작됐는가?
- 누가 이 함수를 잘못된 값으로 호출했는가?
- 그 호출자는 또 누가?
- 발원지까지 거슬러 올라간다
- **발원지에서 수정, 증상에서 수정 금지**

---

### Phase 2: Pattern Analysis

**fix 전에 패턴부터 찾는다.**

#### 2.1 동작하는 예제 찾기

같은 코드베이스 안에서 비슷한 *작동하는* 코드를 찾는다. 무엇이 비슷하고 무엇이 깨졌는가?

#### 2.2 reference 를 *완전히* 읽는다

패턴을 적용하는 거라면 reference 구현을 처음부터 끝까지 읽는다. 훑지 말 것. 모든 줄 다 읽기.

#### 2.3 차이를 나열

작동하는 것과 깨진 것 사이의 *모든* 차이를 list. 작아도 적어라. "그건 상관없을 거야" 라고 가정 금지.

#### 2.4 의존성 이해

이 코드가 의존하는 다른 컴포넌트는? 어떤 setting/config/환경을 필요로 하는가? 어떤 가정을 하고 있는가?

---

### Phase 3: Hypothesis & Testing

**과학적 방법.**

#### 3.1 단일 가설 수립

명확하게 적는다: "Y 때문에 X 가 root cause 라고 본다."
- 모호 금지
- 구체적

#### 3.2 최소 검증

가설을 검증할 *가장 작은* 변경을 한다.
- 한 번에 한 변수
- 여러 개 동시 변경 금지

#### 3.3 검증하고 나서 다음으로

- 됐어? → Phase 4
- 안 됐어? → **새 가설 수립. 이전 fix 를 그대로 둔 채 새 fix 추가 금지.**

#### 3.4 모를 때

- "X 가 이해가 안 된다" 라고 말한다
- 아는 척 금지
- 도움 요청
- 더 조사

---

### Phase 4: Implementation

**root cause 를 수정, 증상을 수정하지 않는다.**

#### 4.1 실패 테스트 작성

- 가장 단순한 재현
- 자동화된 테스트 가능하면 그렇게
- 안 되면 1회용 테스트 스크립트
- **수정 전에 반드시 있어야 함**
- forge 의 `test-driven-development` 스킬을 호출해서 작성

#### 4.2 단일 수정 구현

- root cause 만 해결
- 한 번에 한 변경
- "하는 김에" 개선 금지
- 묶음 리팩터링 금지

#### 4.3 수정 검증

- 테스트가 이제 통과하는가?
- 다른 테스트는 안 깨졌는가?
- 이슈가 실제로 해결됐는가?
- → `verification-before-completion` 스킬의 Gate Function (IDENTIFY → RUN → READ → VERIFY → THEN) 통과 필수

#### 4.4 수정이 안 먹으면

- **STOP**
- 카운트: 지금까지 몇 번 시도했는가?
- 3회 미만 → Phase 1 로 복귀, 새 정보로 재분석
- **3회 이상 → STOP. 아키텍처를 의심하라 (4.5)**
- 4번째 시도 절대 금지 (사용자와 상의 없이는)

#### 4.5 3회 이상 fail 했다면: 아키텍처를 의심하라

같은 fix 패턴을 3번 반복했는데도 새 증상이 계속 다른 곳에서 솟는다면, 문제는 fix 가 아니라 그 자리에 fix 를 박아 넣는 *구조* 자체다. 한 번 멈추고 근본을 다시 본다.

**아키텍처 문제의 패턴:**
- 각 수정이 다른 곳에서 새로운 공유 state / coupling 문제를 드러냄
- 수정이 "대규모 리팩터링" 을 요구
- 각 수정이 다른 곳에서 새 증상을 만듦

**그러면 STOP 하고 근본을 의심:**
- 이 패턴이 근본적으로 옳은가?
- 타성으로 끌고 가고 있는 것은 아닌가?
- 증상 수정을 계속할 게 아니라 아키텍처를 리팩터해야 하는가?

**사용자와 상의한 후에만 추가 수정 시도.**

이건 가설이 틀린 게 아니라 **아키텍처가 틀린 것**이다.

---

## Red Flags — STOP

다음 생각이 들면 그 즉시 Phase 1 로 복귀.

- "지금은 빨리 수정, 조사는 나중에"
- "X 만 바꿔보고 되는지 보자"
- "여러 변경 동시에, 테스트 돌려보자"
- "테스트는 건너뛰고 수동 검증으로"
- "아마 X 일 거야, 그거 수정"
- "완전히 이해는 안 되지만 이게 먹힐 수도"
- "패턴은 X 라는데 나는 다르게 적용할게"
- "주요 문제는 [조사 없이 수정 항목 나열]"
- 데이터 흐름 추적 *전*에 수정 제안
- **"하나만 더 시도" (이미 2회 이상 했을 때)**
- **각 수정이 다른 곳에서 새 문제를 드러냄**

전부 → **STOP. Phase 1 복귀.**

3회 이상 실패 → Phase 4.5 (아키텍처 의심).

---

## 사용자가 보내는 "잘못 가고 있다" 신호

- "그게 안 일어나고 있는 거 아니야?" — 검증 없이 가정함
- "그거 보여줄 수 있어?" — evidence 수집을 안 했음
- "추측 그만" — 이해 없이 fix 제안 중
- "근본부터 다시 생각해봐" / "더 깊게 봐" — 증상이 아니라 fundamentals 를 의심하라
- "막혔어?" (좌절) — 접근 자체가 안 통하고 있다

신호를 보면 → STOP, Phase 1 복귀.

---

## Common Rationalizations

| 변명 | 현실 |
|------|------|
| "단순한 이슈, 프로세스 불필요" | 단순한 버그도 root cause 가 있다. 단순할수록 프로세스가 빠르다 |
| "응급, 프로세스 할 시간 없음" | 체계적 접근이 추측 thrash 보다 빠르다 |
| "일단 이거 시도하고 나서 조사" | 첫 수정이 패턴을 정한다. 처음부터 제대로 |
| "수정이 됐는지 확인하고 테스트는 그 다음에" | 테스트 없는 수정은 회귀를 못 막는다 |
| "여러 수정 동시에 = 시간 절약" | 무엇이 먹혔는지 분리 못함 → 새 버그 |
| "reference 너무 길어서 패턴만 베낀다" | 부분 이해는 버그를 보장 |
| "문제가 보이는데 그냥 수정" | 증상 봄 ≠ root cause 이해 |
| "한 번만 더 시도" (2회 이상 실패 후) | 3회 이상 = 아키텍처 문제. 더 수정하지 말고 패턴을 의심 |

---

## forge 통합 지점

본 스킬의 일차 가치는 *어떤 fail 이 발생했을 때 추측 수정 대신 4-Phase 프로세스를 강제* 하는 것. 호출 위치를 우선순위 순으로:

| 트리거 | 적용 |
|--------|------|
| **`/verify` 5단계 중 어느 것이라도 fail** | "자동 수정" 으로 들어가기 *전* Phase 1 진행. ruff `--fix` 로 자동 수정되는 단순 케이스만 우회 가능 |
| **`/ship` Step 6 (CI 실패)** | 실패 로그를 수정 분류로 직행하기 전에 Phase 1 → 2 진행. evidence 가 "환경 차이" 를 가리키면 그 layer 부터 진단 |
| **`/codex:rescue` 위임** | rescue 에이전트에게 "Phase 1 부터 시작, root cause evidence 가져와" 라고 전달 |
| **단일 작업자의 격리된 디버깅** | 표준 4-Phase 사이클 |

## STAGE 9-4 와의 관계

STAGE 9-4 의 auto-research 루프는 이미 step 3 (실패/저점 항목 분석) 에서 evidence 수집을 수행하고, 9-4 종료 조건의 "3회 연속 rollback" 은 본 스킬의 Phase 4.5 (아키텍처 의심) 와 동일한 의미를 가진다. 본 스킬은 9-4 의 실행 흐름을 바꾸지 않으며, 다만 step 3 의 분석이 어떤 *원리* 로 이루어져야 하는지에 대한 안내를 제공한다.

## STAGE 8 (`/execute-plan`) 와의 관계

STAGE 8 에는 본 스킬이 통합되지 않는다. STAGE 8 의 태스크 fail 처리는 단순 skip + 사용자 보고만 한다 (forge 의 원래 정책). 본격 디버깅은 `/verify` / `/ship` Step 6 / 단일 작업자 컨텍스트에서 일어난다.

---

## When Process Reveals "No Root Cause"

체계적 조사 결과 정말 환경/타이밍/외부 원인이라고 판명되면:

1. 프로세스를 끝낸 것이다
2. 무엇을 조사했는지 문서화
3. 적절한 처리 구현 (retry, timeout, error message)
4. 향후 조사를 위한 monitoring/logging 추가

**하지만:** "no root cause" 사례의 95% 는 **불완전한 조사**다.

---

## Quick Reference

| Phase | 핵심 활동 | 통과 기준 |
|-------|----------|-----------|
| **1. Root Cause** | 에러 읽기, 재현, 변경 확인, evidence 수집 | WHAT 과 WHY 를 이해 |
| **2. Pattern** | working 예제 찾기, 비교 | 차이를 식별 |
| **3. Hypothesis** | 가설 수립, 최소 검증 | 확인 또는 새 가설 |
| **4. Implementation** | 실패 테스트 작성, fix, 검증 | 버그 해결 + 테스트 통과 |

---

## 관련 스킬

- `test-driven-development` — Phase 4.1 의 실패 테스트 작성
- `verification-before-completion` — Phase 4.3 의 수정 검증 (Gate Function 통과)
- `multi-agent-codereview` — 아키텍처 의심 (Phase 4.5) 시 다관점 합의

---

