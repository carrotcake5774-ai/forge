---

name: multi-agent-codereview
description: "다중 전문가 에이전트가 코드베이스를 독립 리뷰하고 토론하여 검증하는 코드 리뷰 스킬. 기술적 관점뿐 아니라 사용자/실무자 관점의 에이전트도 동적으로 구성 가능. Devil's Advocate 필수 포함 + 독립 Task 기반 토론으로 페르소나 독립성 보장. 트리거: 코드 리뷰해줘, 코드 검토해줘, multi-agent code review, 다중 관점 코드 분석, /multi-agent-codereview. 코드 변경사항 리뷰, PR 리뷰, 서비스 레이어 리뷰, 아키텍처 리뷰 요청 시에도 사용."
effort: high
---

# Multi-Agent Code Review

> **호출**: `/multi-agent-codereview {대상}` (파일 경로, 디렉토리, 또는 "최근 변경사항")
> **방식**: Code Analysis -> Role Assignment -> Agent Self-Config -> Independent Review -> 2-Round Debate -> Critical Synthesis -> Final Report
> **모델**: 모든 Agent Task는 `model: "sonnet"` 사용
> **참조**: `references/debate-protocol.md` (토론 프로토콜), `references/quality-gates.md` (QG 상세)

---

## 핵심 원칙

1. **완전 동적 에이전트 구성** -- 고정 카탈로그 없이 Opus가 코드 도메인에 맞춰 역할 지정
2. **기술 + 실무 관점 혼합** -- 백엔드 아키텍트, 보안 전문가뿐 아니라 회계 실무자, UX 사용자 등 도메인 실무 관점도 포함 가능
3. **Devil's Advocate 항상 포함** -- 유일한 고정 역할
4. **독립 Task 기반 토론** -- 단일 LLM 시뮬레이션 대신 각 에이전트가 독립 Task로 발언
5. **에이전트 수 상한 5명** (Devil 포함) -- 비용/품질 균형

---

## Issue 추적 형식 (전 STEP 공통)

```
[ISS-NNN] {쟁점 제목}
  - 상태: OPEN | IN_REVIEW | RESOLVED | ESCALATED
  - 배정: {agent_ids}
  - R1: {에이전트별 입장 요약}
  - R2: {수렴 결과}
  - 최종: {RESOLVED/ESCALATED} -- {결론 요약}
```

---

## 실행 절차

아래 절차를 **정확히 순서대로** 실행하세요. 각 단계의 결과를 변수로 보존하여 다음 단계에 전달합니다.

### 리뷰 대상

```
$ARGUMENTS
```

위 `$ARGUMENTS`가 리뷰 대상입니다 (파일 경로, 디렉토리, "최근 변경사항" 등). 비어 있으면 AskUserQuestion으로 리뷰 대상을 요청하세요.

---

### STEP 0: Code Analysis (Opus 직접)

**오케스트레이터 직접 수행** (Task 호출 불필요):

1. `$ARGUMENTS`에서 리뷰 대상 파악:
   - 특정 파일/디렉토리 → 해당 파일 Read
   - "최근 변경사항" → `git diff HEAD~N` 또는 `git diff --cached` 실행
   - 디렉토리 → `Glob`으로 파일 목록 수집 후 핵심 파일 Read
2. 코드 분석:
   - **프로젝트 도메인** 파악 (회계, 커머스, 헬스케어 등)
   - **기술 스택** 파악 (언어, 프레임워크, DB 등)
   - **변경 범위** 파악 (어떤 모듈/서비스가 영향받는지)
   - **핵심 비즈니스 로직** 식별 (도메인 규칙, 데이터 흐름)
   - **잠재적 쟁점 포인트** 추출 (복잡한 로직, 에러 처리, 성능 병목 등)
3. CLAUDE.md 또는 프로젝트 가이드라인이 있으면 읽어서 컨텍스트에 포함

결과를 `code_analysis`로 보존한다.
핵심 파일 내용을 `code_content`로 보존한다 (에이전트에 전달용).

---

### STEP 1: Role Assignment (Opus 직접)

**오케스트레이터 직접 수행** (Task 호출 불필요):

`code_analysis`를 기반으로 에이전트 구성을 결정한다.

#### 역할 선택 가이드

코드 도메인에 따라 **기술 역할 + 도메인/실무 역할**을 혼합한다:

**기술 역할 후보** (필요한 것만 선택):
- 백엔드 아키텍트, 프론트엔드 엔지니어, DB 전문가, 보안 감사관, QA 엔지니어, DevOps, 성능 엔지니어 등

**도메인/실무 역할 후보** (코드 도메인에 맞춰 선택):
- 회계 실무자 (10년+), 세무사, 쇼핑몰 운영자, 의료 종사자, 물류 관리자, 최종 사용자 등
- 이 역할은 코드의 "비즈니스 로직이 실무와 맞는지"를 검증하는 것이 목적

#### 결정 사항

```markdown
## 에이전트 구성

### 역할 목록
| ID | Role | 관점 | 배정 ISS |
|----|------|------|----------|
| A1 | {역할1} | 기술/실무 | ISS-001, ISS-003 |
| A2 | {역할2} | 기술/실무 | ISS-002, ISS-004 |
| ... | ... | ... | ... |
| DEVIL | Devil's Advocate | 비판적 | ALL |

### Issue 목록
| ID | 쟁점 | 상태 |
|----|------|------|
| ISS-001 | {코드의 핵심 설계 결정 1} | OPEN |
| ISS-002 | {비즈니스 로직 적합성 1} | OPEN |
| ... | ... | ... |
```

**제약**:
- 최소 2명 (전문가 1 + Devil), 최대 5명 (전문가 4 + Devil)
- 사용자가 특정 관점(예: "회계 실무자 관점")을 요청하면 반드시 해당 역할 포함
- Devil's Advocate는 반드시 자동 추가 (id: DEVIL)
- ISS는 코드에서 발견된 설계 결정, 비즈니스 로직, 아키텍처 선택 등 검토가 필요한 포인트
- 모든 ISS에 최소 1명 배정, DEVIL은 ALL

결과를 `role_assignment`로 보존한다.

#### QG0 검증

`references/quality-gates.md`의 QG0 기준에 따라 검증한다.
미통과 시 역할 재조정.

---

### STEP 1.5: Agent Self-Configuration (Task x N, 병렬)

각 에이전트가 독립 Task로 실행되어 자기 설정을 자체 정의한다.

**Task 호출** (에이전트별 병렬, `model: "sonnet"`, `subagent_type: "general-purpose"`):

```
당신에게 '{role}' 역할이 배정되었습니다.
아래 코드를 읽고, 이 역할로서 코드 리뷰하기 위한 자기 설정을 정의하세요.

[출력 형식 -- 반드시 아래 5개 항목을 모두 포함]
## 작업지시서: {role}
- persona: (자신의 전문성/관점/경계를 1인칭으로 서술, 200자 이상)
- review_focus: (집중할 검토 포인트 3~5개, 각 포인트별 구체적 설명)
- review_approach: (리뷰 방법론/프레임워크, 200자 이상. 코드 리뷰이므로 어떤 파일/함수/패턴에 집중할지 구체적으로)
- needed_tools: (Grep, Glob, Read, WebSearch 등 필요 도구, 없으면 '없음')
- severity_criteria: (Critical/Major/Minor 판정 기준을 구체적으로, 200자 이상)

[코드 분석 요약]
{code_analysis}

[핵심 코드]
{code_content}
```

**Devil's Advocate용 추가 지시**:
```
당신은 Devil's Advocate입니다.
코드의 숨겨진 버그, 엣지 케이스, 과도한 복잡성, 실무와의 괴리를 찾는 것이 역할입니다.
다른 에이전트들이 "잘 되어있다"고 평가하는 부분에서도 비판적으로 도전하세요.
```

결과를 `agent_directives` 배열로 보존한다.

#### QG1 검증

`references/quality-gates.md`의 QG1 기준에 따라 검증한다.
미통과 에이전트만 재실행.

---

### STEP 2: Independent Review (Task x N, 병렬)

각 에이전트가 자신의 작업지시서 기반으로 독립 코드 리뷰를 수행한다.

**Task 호출** (에이전트별 병렬, `model: "sonnet"`, `subagent_type: "general-purpose"`):

```
당신은 아래 작업지시서에 따라 행동합니다.
코드를 직접 읽고 분석하세요. 필요하면 Grep, Glob, Read 도구를 사용하세요.

[작업지시서]
{agent_directive}

[리뷰 대상 Issue]
{assigned_issues}

[리뷰 프레임워크 -- 반드시 아래 5개 항목을 모두 포함]
1. 강점 분석 (2-3개, 구체적 코드 위치 file:line 포함)
2. 약점/리스크 (ISS-NNN 형식, 심각도 태그 [Critical]/[Major]/[Minor])
   - 각 약점에 대해: 현상 (코드 위치 포함), 원인 분석, 영향 범위
3. 구체적 개선 제안 (각 약점에 대한 실행 가능한 코드 수정 방향)
4. 확신도: [확정] / [유력] / [확인필요]
5. 전체 평가: [강력지지] / [조건부지지] / [재검토필요] / [반대]
   - 사유 포함

[프로젝트 경로]
{working_directory}

[코드 분석 요약]
{code_analysis}

[핵심 코드]
{code_content}
```

결과를 `reviews` 배열로 보존한다.

#### QG2 검증

`references/quality-gates.md`의 QG2 기준에 따라 검증한다.
미통과 에이전트만 재실행.

---

### STEP 2.5: 리뷰 압축 (Opus 직접)

STEP 3 전달을 위해 각 리뷰를 압축한다.

**압축 형식** (`references/debate-protocol.md` 5절 참조):
```markdown
## 압축 리뷰: {agent_id} ({role})
평가: [강력지지/조건부지지/재검토필요/반대]

| ISS | 심각도 | 핵심 포인트 | 코드 위치 | 확신도 |
|-----|--------|------------|----------|--------|
| ISS-001 | Major | {1줄 요약} | file:line | 유력 |

주요 개선 제안:
1. {제안 1줄 요약}
```

결과를 `compressed_reviews`로 보존한다.

---

### STEP 3: Round 1 Debate (Task x N, 병렬)

각 에이전트가 독립 Task로 타 에이전트 리뷰에 대해 발언한다.

**Task 호출** (에이전트별 병렬, `model: "sonnet"`, `subagent_type: "general-purpose"`):

```
당신은 {role}입니다.
작업지시서: {directive}

다른 에이전트들의 독립 리뷰 결과를 읽고, 각 리뷰에 대해 발언하세요.
필요하면 코드를 직접 읽어 확인하세요 (프로젝트 경로: {working_directory}).

[발언 규칙]
1. 각 에이전트의 리뷰를 ISS별로 직접 인용하여 동의/반론
2. 반론 시 근거 필수 -- 코드를 직접 확인한 결과를 인용 (감정적/모호한 반론 금지)
3. 새 Issue 발견 시 ISS-NNN 형식으로 추가 (최대 2개)
4. 각 ISS에 상태 제안: OPEN -> IN_REVIEW
5. ISS별 발언 최대 300자

[발언 형식]
### [ISS-NNN]에 대해
- 대상: {target_agent_id}의 주장
- 입장: [동의] / [반론]
- 근거: ...
- (반론 시) 대안: ...

[타 에이전트 리뷰 요약]
{compressed_reviews}

[핵심 코드]
{code_content}
```

결과를 `debate_round1` 배열로 보존한다.

#### QG3 검증

`references/quality-gates.md`의 QG3 기준에 따라 검증한다.
미통과 에이전트만 재실행.

---

### STEP 3.5: R1 토론 압축 (Opus 직접)

STEP 4 전달을 위해 R1 발언을 압축한다.
- 에이전트별 반론/동의 요약
- ISS별 상태 집계

결과를 `compressed_debate_r1`으로 보존한다.
각 에이전트의 R1 발언 원문도 `my_r1_statements`로 개별 보존한다.

---

### STEP 4: Round 2 Debate (Task x N, 병렬)

R1 반론에 대해 수렴 응답한다.

**Task 호출** (에이전트별 병렬, `model: "sonnet"`, `subagent_type: "general-purpose"`):

```
Round 2 수렴 토론. R1에서 당신에게 제기된 반론에 응답하세요.

당신은 {role}입니다.
작업지시서: {directive}

[응답 규칙]
1. [수용] 또는 [유지-재반론]으로 응답 (동일 근거 반복 금지)
2. 합의 가능 Issue -> RESOLVED 제안
3. 합의 불가 Issue -> ESCALATED 제안 + 양측 근거 기록
4. 반론 응답별 최대 200자

[Devil 추가 규칙 (DEVIL만 해당)]
- '합의의 블라인드스팟' 최종 점검
- RESOLVED 직전 이의 제기 1회 가능

[R1 토론 요약]
{compressed_debate_r1}

[나의 R1 발언]
{my_r1_statement}
```

결과를 `debate_round2` 배열로 보존한다.

#### QG4 검증

`references/quality-gates.md`의 QG4 기준에 따라 검증한다.

**R3 트리거 판정**: RESOLVED < 50%이면 R3 실행.
- Opus가 미해결 쟁점을 A안/B안으로 축소 제시
- 각 에이전트가 택일 (추가 Task x N, 최대 1라운드)

---

### STEP 4.5: 전체 토론 종합 압축 (Opus 직접)

STEP 5 전달을 위해 전체 과정을 ISS별 최종 상태 + 핵심 근거로 종합한다.

```markdown
## 종합 압축

### 참여 에이전트
| ID | Role | 관점 | 자기 설정 요약 (1줄) |
|----|------|------|---------------------|
| A1 | ... | 기술 | ... |
| A2 | ... | 실무 | ... |
| DEVIL | Devil's Advocate | 비판적 | ... |

### ISS 최종 상태
| ISS | 상태 | R1 핵심 | R2 결론 | 핵심 근거 | 코드 위치 |
|-----|------|---------|---------|----------|----------|
| ISS-001 | RESOLVED | ... | ... | ... | file:line |
| ISS-002 | ESCALATED | ... | ... | 양측: ... | file:line |

### 주요 합의 사항
- ...

### 미해결 쟁점
- ...

### Devil 블라인드스팟
- ...
```

결과를 `synthesis_input`으로 보존한다.

---

### STEP 5: Critical Synthesis (Task x 1)

전체 토론 요약본 기반 합의 보고서를 생성한다.

**Task 호출** (`model: "sonnet"`, `subagent_type: "general-purpose"`):

```
전체 코드 리뷰 토론 결과를 종합하여 합의 보고서를 작성하세요.

[보고서 구조 -- 반드시 아래 9개 섹션을 모두 포함]

## 1. 코드 개요
- 리뷰 대상 코드 요약 (프로젝트, 변경 범위, 기술 스택)

## 2. 참여 에이전트 및 자체 설정 요약
- 각 에이전트의 역할, 관점(기술/실무), 검토 초점 요약

## 3. Issue 추적표
| ISS | 쟁점 | 초기 상태 | R1 | R2 | 최종 상태 | 코드 위치 |
|-----|------|----------|-----|-----|----------|----------|
| ISS-001 | ... | OPEN | ... | ... | RESOLVED/ESCALATED | file:line |

## 4. 합의 사항
- 전원 합의 항목 + 근거

## 5. 조건부 합의
- 다수 합의 + 소수 반대 항목 (소수 의견 기록)

## 6. 미합의 ESCALATED
- 합의 불가 항목 + 양측 근거 + 사용자 판단 요청

## 7. 블라인드스팟 경고
- Devil's Advocate가 제기한 숨겨진 위험 요소

## 8. 종합 평가
- 코드 품질: [우수/양호/보통/미흡]
- 실무 적합성: [적합/보완필요/재설계필요] (실무 관점 에이전트가 있는 경우)
- 배포 준비도: [즉시배포/보완후배포/재작업필요]
- 종합 소견 (3-5문장)

## 9. 권고 액션 아이템
- 우선순위순 정렬 (즉시수정 / 다음스프린트 / 향후검토)
- 각 항목에 담당 제안 + 코드 수정 방향 + 예상 효과

[입력 -- 전체 요약본]
{synthesis_input}
```

결과를 `synthesis_report`로 보존한다.

#### QG5 검증

`references/quality-gates.md`의 QG5 기준에 따라 검증한다.

---

### STEP 6: Final Report (Opus 직접)

`synthesis_report`를 사용자 채팅으로 출력한다.

보고서 끝에 다음 메타정보를 추가:

```
---
## 검증 프로세스 완료
- 방식: Multi-Agent Code Review (독립 리뷰 -> 2-Round 토론 -> Critical Synthesis)
- 에이전트: {N}명 ({역할 목록})
- 관점: {기술 N명, 실무 M명, Devil 1명}
- 토론 라운드: {R}회
- Issue 추적: {총 ISS}건 중 RESOLVED {n}건, ESCALATED {m}건
- 모델: Claude Sonnet (서브에이전트)

본 분석은 AI 기반 다중 관점 코드 검토이며, 최종 의사결정은 담당자의 판단이 필요합니다.
```

---

## 오케스트레이션 규칙

1. **모든 Task 호출 시 `model: "sonnet"` 필수** -- Opus 위임 금지
2. **STEP 0, 1, 2.5, 3.5, 4.5, 6은 오케스트레이터 직접 수행** -- Task 불필요
3. **STEP 1.5, 2, 3, 4는 에이전트별 병렬 실행** -- Fan-out 패턴
4. **STEP 5는 단일 Task** -- 종합 합의
5. **중간 결과 보존** -- 각 STEP 산출물을 변수로 보존하여 다음 단계에 전달
6. **컨텍스트 압축** -- STEP 간 전달 시 Opus가 압축 (원문 대비 ~30%), 토큰 예산 ~80K 이내
7. **코드 직접 접근** -- 에이전트에게 프로젝트 경로를 전달하여 필요시 Grep/Read로 코드를 직접 확인 가능

## 컨텍스트 압축 전략

| 전달 시점 | 압축 방식 |
|----------|----------|
| STEP 2 -> 3 | 각 독립 리뷰를 ISS별 핵심 포인트 + 코드 위치 + 평가로 압축 |
| STEP 3 -> 4 | R1 발언을 에이전트별 반론/동의 요약으로 압축 |
| STEP 4 -> 5 | 전체 과정을 ISS별 최종 상태 + 핵심 근거로 종합 |

## 에러 처리

- Agent 응답이 비정상적으로 짧은 경우: QG에서 탐지 -> 1회 재실행
- 2회 재실행 후 미통과: 사용자 에스컬레이션 (미통과 항목 + 산출물 표시)
- 병렬 Task 중 일부 실패: 성공한 에이전트 결과로 진행, 실패 에이전트를 1회 재실행

## 리소스

### references/
- `debate-protocol.md` -- 토론 프로토콜 (라운드 규칙, 합의 조건, 발언 형식, 압축 규칙)
- `quality-gates.md` -- QG0~5 상세 기준 + 미통과 처리
