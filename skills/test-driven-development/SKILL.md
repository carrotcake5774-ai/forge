---
name: test-driven-development
description: "구현 코드 작성 전에 실패하는 테스트를 먼저 짜서 RED-GREEN-REFACTOR 사이클을 강제하는 스킬. 격리된 단일 버그 수정, /ship Step 6 의 CI 실패 fix, /pipeline STAGE 9-2 의 Gold gap-closing test 작성에서 호출. 트리거: '버그 재현', '재현 테스트', '회귀 테스트 작성', '단일 버그 수정', 'Gold gap-closing test', 'eval 항목 gap-closing'"
effort: medium
---

# Test-Driven Development (TDD)

> **호출**: 격리된 단일 버그 수정, `/ship` Step 6 의 CI 실패 fix 작성, `/pipeline` STAGE 9-2 의 gap-closing Gold test 작성
> **금지 위치**: `/execute-plan` 의 병렬 wave 내부. STAGE 8 은 의도적으로 verification 을 STAGE 9 / `/verify` 로 위임하므로 wave 안에 테스트 사이클을 박지 않는다 (layer 위반)
> **방식**: RED → Verify RED → GREEN → Verify GREEN → REFACTOR → Repeat
> **출처**: 표준 TDD 의 RED-GREEN-REFACTOR 패턴. forge 는 STAGE 9 의 자체 검증 루프(출제자 ≠ 응시자)가 더 강한 anti-gaming 을 이미 제공하므로, 본 스킬의 가치는 *단일 작업자 컨텍스트* 의 fix discipline 에 한정된다

---

## 핵심 원칙

**테스트가 실패하는 모습을 직접 보지 않았다면, 그 테스트가 올바른 것을 검증하는지 알 수 없다.**

> 규칙의 자구를 어기는 것은 규칙의 정신을 어기는 것이다.

---

## When to Use

본 스킬이 호출되는 컨텍스트 (단일 버그 수정, `/ship` Step 6 의 CI 실패 fix, `/pipeline` STAGE 9-2 의 gap-closing Gold test 작성) 는 **정의상 모두 runtime behavior 를 다루는 작업** 이다. 이 컨텍스트에서는 면제가 정의상 발생하지 않으므로 TDD 가 항상 적용된다.

문서/주석 변경, 단순 rename, 타입 hint 추가 등의 작업은 본 스킬이 호출되는 컨텍스트에 들어오지 않는다 — 그것들은 일반 편집 작업이고 별도의 게이트 (lint, format) 만 통과하면 된다.

"이번 한 번만 TDD 건너뛰자" 라는 생각이 본 스킬의 호출 컨텍스트에서 든다면 멈춘다. 그게 합리화다.

---

## Iron Law

```
실패하는 테스트 없이 production 코드를 작성하지 않는다.
```

테스트보다 먼저 코드를 썼는가? **삭제. 다시 시작.**

예외 없음:
- "참고용으로 남겨두기" 금지
- "테스트 짜면서 적당히 가져다 쓰기" 금지
- 보지도 말 것
- 삭제는 삭제다

테스트부터 다시 구현한다. 끝.

---

## Red-Green-Refactor 사이클

### RED — 실패 테스트 작성

가장 작은 단위로 "이게 무엇을 해야 하는가"를 표현하는 테스트 1개를 작성.

**요건:**
- 한 번에 한 가지 동작
- 이름이 동작을 명확히 서술 (`test_retries_three_times`, `test_rejects_empty_email`)
- 실제 코드 사용 (mock은 불가피한 경우만)
- forge 규칙: **DB가 필요한 테스트는 실제 PostgreSQL 사용** (mock 금지)

### Verify RED — 실패하는 모습을 직접 본다 (필수, 절대 건너뛰지 말 것)

```bash
uv run pytest path/to/test_x.py::test_y -q
```

확인사항:
- 테스트가 **실패**한다 (에러가 아니라 실패)
- 실패 메시지가 예상한 형태다
- 실패 사유가 "기능이 없어서"다 (오타나 import 에러가 아니라)

**테스트가 처음부터 통과한다면** → 기존 동작을 테스트하고 있는 것. 테스트를 고친다.
**테스트가 에러로 죽는다면** → 에러부터 고치고, 정상적으로 실패할 때까지 재실행.

### GREEN — 최소 코드로 통과

테스트를 통과시킬 *가장 단순한* 코드를 작성.

- 테스트가 요구하지 않는 기능 추가 금지
- 다른 코드 리팩터링 금지
- "하는 김에" 개선 금지
- YAGNI

### Verify GREEN — 통과하는 모습을 직접 본다 (필수)

```bash
uv run pytest path/to/test_x.py::test_y -q
```

확인:
- 해당 테스트 PASS
- **다른 테스트가 깨지지 않음** — 영향 모듈 전체 재실행
- 출력 깨끗함 (경고, 에러 없음)

본 스킬은 forge 의 직렬 구간(STAGE 9 / `/ship` Step 6 / 단일 버그 수정)에서만 호출되므로 영향 영역 회귀에 race 위험이 없다. 병렬 wave 내부 호출은 위 "호출 금지 위치" 표 참조.

### REFACTOR — 정리 (green 인 상태에서만)

- 중복 제거
- 이름 개선
- 헬퍼 추출

테스트는 계속 green. 동작 추가 금지.

### Repeat

다음 동작을 위한 다음 실패 테스트로.

---

## Good Tests vs Bad Tests

| 품질 | Good | Bad |
|------|------|-----|
| **최소성** | 한 가지만 검증. 이름에 "and" 들어가면 분리 | `test_validates_email_and_domain_and_whitespace` |
| **명확성** | 이름이 동작을 서술 | `test_1`, `test_works` |
| **의도** | 원하는 API 형태를 보여줌 | 구현 디테일을 노출 |

---

## 왜 순서가 중요한가

**"구현 다음에 테스트로 검증하면 되잖아"**

나중에 작성한 테스트는 처음부터 통과한다. 처음부터 통과하면 아무것도 입증하지 못한다.
- 잘못된 것을 테스트할 수 있다
- 동작이 아니라 구현을 테스트할 수 있다
- 잊어버린 edge case 를 못 잡는다
- 테스트가 실제로 무언가 잡아내는 모습을 본 적이 없다

테스트를 먼저 작성하면 실패하는 모습을 강제로 보게 되어, 그 테스트가 실제로 무언가 검증한다는 게 입증된다.

**"이미 X시간 작성한 코드를 지우는 건 낭비잖아"**

매몰비용 오류. 이미 흘러간 시간이다. 지금의 선택지:
- 지우고 TDD 로 다시 (X시간 더, 신뢰도 높음)
- 그대로 두고 사후 테스트 추가 (30분, 신뢰도 낮음, 버그 가능성 높음)

진짜 낭비는 **신뢰할 수 없는 코드를 떠안는 것**이다.

---

## Common Rationalizations

| 변명 | 현실 |
|------|------|
| "너무 단순해서 테스트 불필요" | 단순한 코드도 깨진다. 테스트는 30초면 짠다. |
| "나중에 테스트 짤게" | 사후 테스트는 처음부터 통과 = 아무것도 입증 못함 |
| "이미 수동으로 다 테스트했어" | ad-hoc ≠ systematic. 기록도 없고 재실행도 못함 |
| "이미 X시간 썼는데 지우는 건..." | 매몰비용. 신뢰 불가 코드 보존이 더 큰 부채 |
| "참고용으로만 남겨두고 새로 테스트부터" | 결국 그걸 베낀다. 그게 사후 테스트다. delete 는 delete |
| "탐색이 필요해" | OK. 탐색 코드는 버려라. TDD 로 새로 시작 |
| "TDD 가 나를 느리게 만든다" | TDD 가 사후 디버깅보다 빠르다 |
| "기존 코드도 테스트가 없는데" | 네가 손대는 부분이다. 손대는 부분만이라도 테스트 추가 |

---

## Red Flags — STOP & Start Over

- 테스트보다 먼저 코드 작성
- 테스트가 첫 실행에서 통과
- 왜 fail 했는지 설명 못함
- 테스트를 "나중에" 추가
- "이번 한 번만"
- "이미 수동으로 다 해봤어"
- "참고용으로", "비슷하게 가져다 쓰자"
- "이미 작성한 거 지우긴 아깝잖아"
- "TDD 는 dogmatic, 나는 pragmatic"
- "이건 좀 달라서..."

전부 → **삭제. TDD 로 처음부터 다시.**

---

## forge 통합 지점

본 스킬의 일차 가치는 **단일 작업자 컨텍스트의 fix discipline** 이다. 호출 위치를 우선순위 순으로:

| 호출 위치 | 적용 방식 |
|----------|----------|
| **격리된 단일 버그 수정** | 표준 RED-GREEN-REFACTOR 사이클. 사용자가 직접 또는 단일 agent 가 한 버그를 수정할 때 |
| **`/ship` Step 6: CI 실패 fix** | CI 로그에서 식별된 회귀에 대해 재현 테스트 작성 → fail 확인 → 수정 → PASS 확인 → 임시 revert → 다시 fail 확인 (true 회귀 입증) |
| **`/pipeline` STAGE 9-2: gap-closing Gold test 작성** | 별도 세션이 Gold test 를 작성할 때, *gap-closing* (구현 안 된 동작) 카테고리는 현재 코드에서 fail 함을 확인. 통과하면 폐기 후 재작성. *anchor* (이미 잘 동작하는 회귀 방지) 카테고리는 RED 강제 안 함 |

## 호출 안 되는 위치

`/execute-plan` 의 병렬 wave 내부와 태스크별 처리. STAGE 8 은 의도적으로 가벼운 lint 만 하고 모든 verification (테스트 실행 포함) 은 §5 의 `/verify` 와 STAGE 9 로 위임된다. 본 스킬을 wave 안에 박는 것은 그 layer 분리를 위반한다.

## STAGE 9-4 와의 관계

STAGE 9-4 의 auto-research 루프는 이미 자체적으로 RED check (step 6 의 Gold fail = 즉시 rollback), fresh evidence (step 7 새 점수), commit/rollback 판정 (step 8) 을 수행한다. **본 스킬은 9-4 의 실행 흐름을 바꾸지 않는다** — 다만 9-4 step 4 의 한 *수정* 이 어떻게 이루어져야 하는지에 대한 원리적 안내를 제공한다 (안내는 자동 강제가 아님). 9-4 의 진짜 검증은 forge 의 출제자/응시자 분리가 한다.

---

## 버그 수정 적용 패턴

1. 버그를 재현하는 테스트 작성 (RED)
2. 그대로 돌려서 fail 확인 (현재 코드가 정말 그 버그를 가지고 있음을 입증)
3. 최소 수정
4. PASS 확인
5. 수정을 일시 revert → 다시 fail (회귀 테스트가 진짜인지 입증)
6. 수정 복원 → PASS

이 6단계는 `verification-before-completion` 스킬의 재현 테스트 입증 규칙과 동일.

---

## Verification Checklist

작업을 완료로 표시하기 *전에*:

- [ ] 새 함수/메서드마다 테스트가 있다
- [ ] 각 테스트가 실패하는 모습을 직접 확인했다
- [ ] 실패 사유가 "기능 부재"였다 (오타/import 에러 아님)
- [ ] 테스트를 통과시키는 *최소* 코드를 작성했다
- [ ] 모든 테스트 PASS
- [ ] 출력 깨끗함 (경고, deprecation 없음)
- [ ] mock 없이 실제 코드 사용 (불가피한 경우 명시)
- [ ] edge case 와 에러 경로도 커버
- [ ] **DB 가 필요한 케이스는 실제 PostgreSQL 에서 실행** (forge 규칙)

전부 체크 못함 → TDD 를 안 한 것. 처음부터 다시.

---

## When Stuck

| 문제 | 해결 |
|------|------|
| 테스트를 어떻게 짜야 할지 모르겠다 | 원하는 API 를 먼저 그려본다. assertion 부터 쓴다. 사용자에게 묻는다 |
| 테스트가 너무 복잡 | 설계가 너무 복잡. 인터페이스 단순화 |
| 모든 걸 mock 해야 함 | 코드 결합도 과다. dependency injection 도입 |
| 테스트 setup 거대 | 헬퍼 추출. 그래도 복잡 → 설계 단순화 |

---

## Final Rule

```
production 코드 → 그것을 검증하는 실패 테스트가 먼저 있었다
그게 아니면 → TDD 가 아니다
```

자동 면제 목록 또는 사용자의 명시적 허가 없이는 예외 없음.

---

## 관련 스킬

- `verification-before-completion` — RED/GREEN 의 fresh 출력 입증
- `systematic-debugging` — 테스트 fail 의 root cause 분석 (Phase 4.1 의 실패 테스트 작성을 본 스킬이 담당)
- `commands/ship.md` — Step 6 의 CI 실패 fix 컨텍스트
- `commands/pipeline.md` — STAGE 9-2 의 gap-closing Gold test 작성 컨텍스트
