# /pipeline — 전체 개발 파이프라인 오케스트레이션

> version: 2.1.0 | last_modified: 2026-04-02

아이디어부터 커밋까지 12단계 파이프라인을 자동 체이닝합니다.
각 단계 완료 후 다음 단계로 자동 전환하되, 사용자 판단이 필요한 지점에서만 멈춥니다.

### 실행 모델: 혼합 (Hybrid)

- **STAGE 간**: 순차 실행 (1→2→3→...→12)
- **STAGE 내부**: Task 병렬 가능 (STAGE 8의 wave별 병렬, STAGE 9의 iteration 등)
- **롤백 단위**: STAGE 단위. `--from N`은 해당 STAGE 전체를 재실행
- **STATE.md**: STAGE 레벨 상태만 추적 (Task 레벨 추적 불필요)

### STAGE별 사용자 개입 맵

```
 STAGE  모드        사용자 액션
 ─────  ────────    ─────────────────────────────
  1     입력 필요    아이디어/자료 제공
  2     입력 필요    인터뷰 응답 (대규모 시 Gemini CLI 자동 호출)
  3     자동         Gemini CLI 자동 호출 (plan-mode + git-guard)
  4     자동         /agent-team-planner 실행
  5     자동         /multi-agent-review 실행
  6     자동         Gemini CLI 자동 호출 (plan-mode + git-guard)
  7     승인 필요    최종 플랜 확인 (y/n)
  8     자동         /plan-to-tasks → /execute-plan
  9     자동         Evaluator 설계 + Auto-research 루프
 10     자동         /multi-agent-codereview 실행
 11     자동         /codex:review + /codex:adversarial-review
 12     승인 필요    파일 스테이징 확인 → 커밋/푸시
```

## 경로 분기: Fast Track / Full Track

STAGE 1의 **예상 복잡도** 판정에 따라 파이프라인 경로가 분기됩니다.

```
Fast Track (복잡도: Low)
  STAGE 1 → 2a → 5 → 8 → 9 → 10 → 12
  (STAGE 3/4/6/7/11 생략 — 외부 리뷰 + 에이전트 팀 설계 불필요)
  실패 시 롤백: STAGE 5로 복귀 → 5 재실행 → 8부터 재개

Full Track (복잡도: Medium / High)
  STAGE 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12
  (전체 12단계)
  실패 시 롤백: STAGE 7 회귀 판단 기준 참조
```

| 복잡도 | 기준 | 경로 |
|--------|------|------|
| **Low** | 변경 파일 5개 이하 + 신규 모듈 없음 + 아키텍처 변경 없음 | Fast Track |
| **Medium** | 변경 파일 6개 이상 또는 기존 모듈 확장 | Full Track |
| **High** | 신규 모듈 + 아키텍처 변경 + 다중 패키지 영향 | Full Track |

## 인자

- `$ARGUMENTS`: 시작 지점 + 옵션
  - 비어있으면 → STAGE 1부터 시작
  - `--from N` → STAGE N부터 시작 (이전 단계 산출물이 이미 있을 때)
  - `--plan path/to/plan.md` → STAGE 2의 플랜 파일 지정
  - `--skip-external` → Gemini 외부 리뷰(STAGE 3, 6, 11) 건너뛰기
    - 품질 게이트는 내부 리뷰로 대체:
      - STAGE 3 스킵 → STAGE 5(/multi-agent-review)의 CRITICAL 0건으로 충족
      - STAGE 6 스킵 → STAGE 5 결과가 이미 반영된 상태로 STAGE 7 진행
      - STAGE 11 스킵 → STAGE 10(/multi-agent-codereview)으로 충족 (Codex 리뷰 생략)

### 입력 검증

`--from N`의 N은 1~12 범위만 허용. 범위 외 값은 에러 출력 후 종료.
`--from N` 재개 시 STATE.md 존재 여부를 먼저 확인하고, 없으면 사용자에게 경고 후 계속 여부 확인.

---

## 파이프라인 전체 구조

```
╔══════════════════════════════════════════════════════════╗
║  Phase A: 아이디어 → 초안 플랜                           ║
║  ┌─────────────────────────────────────────────────┐    ║
║  │ STAGE 1: 아이디어 평가 (적용 여부 판단)           │    ║
║  │ STAGE 2: 플랜 초안 작성 (PRD 형식)               │    ║
║  │ STAGE 3: Gemini 외부 리뷰 + 반영 (2-3회 루프)     │    ║
║  └─────────────────────────────────────────────────┘    ║
╠══════════════════════════════════════════════════════════╣
║  Phase B: 구현 계획 고도화                               ║
║  ┌─────────────────────────────────────────────────┐    ║
║  │ STAGE 4: /agent-team-planner (구현 계획 고도화)   │    ║
║  │ STAGE 5: /multi-agent-review (내부 2차 고도화)    │    ║
║  │ STAGE 6: Gemini 외부 리뷰 + 반영 (2-3회 루프)     │    ║
║  │ STAGE 7: 최종 플랜 확정                          │    ║
║  └─────────────────────────────────────────────────┘    ║
╠══════════════════════════════════════════════════════════╣
║  Phase C: 구현 + 자동 개선                               ║
║  ┌─────────────────────────────────────────────────┐    ║
║  │ STAGE 8: /plan-to-tasks → /execute-plan         │    ║
║  │ STAGE 9: Evaluator 설계 + Auto-research 루프     │    ║
║  └─────────────────────────────────────────────────┘    ║
╠══════════════════════════════════════════════════════════╣
║  Phase D: 코드 리뷰 + 배포                               ║
║  ┌─────────────────────────────────────────────────┐    ║
║  │ STAGE 10: /multi-agent-codereview (내부 1차 수정) │    ║
║  │ STAGE 11: Codex 외부 코드 리뷰 (자동, 2-3회)      │    ║
║  │ STAGE 12: /verify → /ship                       │    ║
║  └─────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════╝
```

---

## STAGE 1: 아이디어 평가

아이디어 또는 웹서치 결과를 분석하여 적용 여부를 판단합니다.

1. 사용자에게 아이디어/자료를 요청 (텍스트, URL, 파일)
2. 프로젝트 컨텍스트(CLAUDE.md, 현재 Phase) 대비 분석:
   - 현재 Phase 범위에 포함되는가
   - 기술적으로 실현 가능한가
   - DO NOT Rules에 위반되지 않는가
   - 투자 대비 가치(ROI)가 있는가
3. 판정 출력:
   ```
   === STAGE 1: 아이디어 평가 ===
   판정: ✅ 적용 가능 / ❌ 부적합
   사유: ...
   영향 범위: 프론트엔드 3파일, 백엔드 2파일
   예상 복잡도: Low / Medium / High
   파이프라인 경로: Fast Track / Full Track
   ```
4. ✅이면 복잡도에 따라 경로 분기:
   - **Low** → Fast Track (1→2a→5→8→9→10→12)
   - **Medium / High** → Full Track (전체 12단계)

---

## STAGE 2: 플랜 초안 작성 (PRD 형식)

STAGE 1의 분석 결과를 기반으로 구조화된 플랜을 작성합니다.

### 2-1. 규모 판단

| 규모 | 기준 | 작성 경로 |
|------|------|----------|
| 소규모 | 변경 파일 5개 이하 | **2a. Claude 단독** |
| 대규모 | 변경 파일 6개 이상 또는 신규 모듈 | **2b. Gemini 초안 경로** |

### 2a. Claude 단독 작성

1. **사전 인터뷰** (AskUserQuestion, 1-2 라운드):
   - 라운드 1: 핵심 요구사항, 우선순위, 제약 조건 확인
   - 라운드 2: 트레이드오프 선택, 미결 사항 확인
   - 설계서에 직접 답이 나오지 않는 것만 질문 (상투적 질문 금지)
2. 인터뷰 결과 + STAGE 1 분석으로 플랜 작성

### 2b. Gemini 초안 경로

상세 프로세스: `.claude/docs/plan_build_process_with_gem.md`

1. Claude가 **Gemini용 브리핑** 작성 → `.claude/prompts/{플랜명}-briefing.md`
   - 프로젝트 개요, 현재 코드 상태, 기술 스택
   - IMMUTABLE CONSTRAINTS (DO NOT 규칙 전문)
   - 이번 플랜의 목표/범위
2. Claude가 `Bash` 툴로 Gemini CLI 자동 호출 → 초안 수신
   - `gemini -p "$(cat .claude/prompts/{플랜명}-briefing.md)" --approval-mode plan -o text > .claude/prompts/{플랜명}-draft-raw.md`
   - `--approval-mode plan` (read-only) + git-guard로 파일 수정 방지
3. Claude가 정제:
   - DO NOT Rules 위반 항목 제거
   - 추상적 아이디어 → 구체적 모델/서비스/API 설계로 변환
   - 비현실적 범위 → Phase로 분할

### 플랜 템플릿 (PRD 형식)

파일명: `.claude/plans/{플랜명}_draft.md` (kebab-case)

```markdown
# {플랜명} — v1.0

## 1. 문제 정의 / 목표
- 해결할 문제
- 성공 기준

## 2. 변경 범위
| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| path/to/file.py | 수정 | ... |

## 3. Task 목록

### Task 1: {제목}
parallel: false
depends_on: []

- 구현 상세 내용

#### 완료 기준
- [ ] 검증 가능한 기준 1
- [ ] 검증 가능한 기준 2

### Task 2: {제목}
parallel: true
depends_on: [task_1]

- 구현 상세 내용

#### 완료 기준
- [ ] 검증 가능한 기준 1

## 4. 설계 결정 기록 (ADR)

### {결정 사항}
- **컨텍스트**: 왜 이 결정이 필요했는지
- **결정**: 선택한 방향
- **근거**: 결정 이유
- **기각된 대안**: 검토했다가 버린 옵션과 이유
- **결과**: 이 결정이 가져오는 트레이드오프

## 5. 리스크 & 미결 사항

| 항목 | 유형 | 우선순위 | 상태 |
|------|------|----------|------|
| ... | 기술/운영/데이터 | High/Med/Low | 미결/완료 |

## 6. 검증 방법
- 단위 테스트 / 통합 테스트 전략
- 수동 검증 시나리오
```

### PRD 태그 규칙

| 태그 | 동작 |
|------|------|
| `parallel: true` | 같은 wave의 다른 Task와 동시 실행 |
| `parallel: false` | 단독 순차 실행 (기본값) |
| `depends_on: []` | 의존성 없음 (즉시 실행 가능) |
| `depends_on: [task_1, task_2]` | 선행 Task 완료 후에만 실행 |

이 태그는 STAGE 8에서 `/plan-to-tasks`가 파싱하여 실행 순서를 결정합니다.

### 사용자 확인

플랜 초안 완성 후 사용자에게 확인 요청. 수정 요청 시 반영 후 재확인.

---

## STAGE 3: Gemini 외부 리뷰 (플랜 초안, 2-3회)

Gemini에서 플랜 초안을 다중 유형 프롬프트로 교차검증합니다.
상세 프로세스: `.claude/docs/plan_build_process_with_gem.md`

### 리뷰 유형 동적 설계 (Opus)

프로젝트마다 리뷰 관점이 다르므로, Opus가 플랜과 프로젝트 컨텍스트를 분석하여 리뷰 유형을 설계합니다.

**고정 규칙**:
- **Type A(파괴)는 필수** — 항상 1종 이상 비판적 분석 포함
- **최소 2종, 최대 4종**
- 각 유형에 범위 제한을 명시 (Type A는 "새 기능 제안 금지" 등)

**Opus가 결정하는 것**:

| 항목 | 설명 |
|------|------|
| 유형 수 | 2~4종 (프로젝트 규모/성격에 따라) |
| 각 유형의 이름·목적·초점 | 프로젝트 도메인에 맞게 설계 |
| 유형별 Gemini 지시 | 범위 제한, 웹서치 요청 여부, 창의 범위 |

**예시 — 프로젝트별 유형 구성**:

| 프로젝트 | Type A | Type B | Type C | Type D |
|---------|--------|--------|--------|--------|
| 회계 SaaS | 파괴 (기술 결함) | 발견 (K-GAAP 실무) | 디자인 (UI/UX) | — |
| 의료 시스템 | 파괴 (기술 결함) | 규정 (건강보험 청구) | 보안 (HIPAA) | 디자인 |
| CLI 도구 | 파괴 (기술 결함) | UX (사용성/에르고노믹스) | — | — |

### 프롬프트 생성 규칙 (고정)

1. **자기완결형**: 공통 브리핑 + 개별 질문이 합쳐진 완성본. `gemini -p "$(cat ...)"` 한 번 호출로 전달 가능
2. **1 프롬프트 = 1 파일**: `.claude/prompts/{플랜명}-{버전}/input/{Type}{번호}_{topic}.md`
3. **공통 브리핑 매번 포함**: "아까 보낸 거 참고해" 금지 — Gemini 할루시네이션 방지
4. **IMMUTABLE CONSTRAINTS 전문 매번 삽입**: 축약/참조 금지
5. **각 프롬프트는 별도 `gemini` CLI 호출로 실행**: 호출 간 컨텍스트 격리로 세션 오염 차단
6. **산출물 형식 강제**: ID 채번 + 심각도/우선순위 + 요약 테이블 (Claude 파싱용)
7. **Type A는 범위 제한 명시**, 나머지 유형은 창의 범위를 열되 CONSTRAINTS만 울타리
8. **플랜 수정 금지 지시 필수**: 프롬프트 말미에 "원본 플랜 수정 금지. 리뷰 리포트만 stdout으로 출력. 파일 생성/수정 금지." 강제 문구 삽입 — Gemini가 "리뷰"를 "개선 작업"으로 해석해 파일을 수정하는 경향에 대한 이중 방어 (`--approval-mode plan` + 프롬프트 강제 + git-guard의 3중 방어 중 2단계)

### 루프 구조 (Gemini CLI 자동화)

```
version = 현재 플랜 버전 (예: v1.0)
round = 1
while round <= 3:
    1. Claude가 ABC 프롬프트 생성 → .claude/prompts/{플랜명}-{version}/input/
       - Feature별 좁은 범위로 분할 (전체 리뷰 금지)
       - 각 프롬프트 말미에 "원본 플랜 수정 금지, 리뷰 리포트만 stdout 출력" 강제 문구 삽입 (규칙 #8)

    2. Claude가 Bash 툴로 각 input 파일을 gemini CLI로 자동 호출:
       - Pre-check: `BEFORE=$(git status --porcelain)` 스냅샷 저장
       - 호출:
           gemini -p "$(cat .claude/prompts/{플랜명}-{version}/input/{파일}.md)" \
             --approval-mode plan \
             -o text \
             > .claude/prompts/{플랜명}-{version}/output/{파일}.md
         · `--approval-mode plan` → read-only 모드, 파일 수정 원천 차단
         · `-o text` → stdout 파싱 용이
         · 각 프롬프트는 독립 호출 (세션 간 컨텍스트 격리)
       - Post-check: `AFTER=$(git status --porcelain)` 재확인
         · BEFORE == AFTER → 정상, output 유지
         · BEFORE != AFTER → 수정 감지:
             a. `git checkout -- .` 로 즉시 rollback
             b. 해당 output/{파일}.md 폐기 (rm)
             c. 경고 로그 기록 + 수동 개입 큐로 분리
             d. 해당 프롬프트는 다음 라운드에서 재시도

    3. Claude가 output/*.md 파싱 + 분류:
       - 반영: 유의적 + 실현 가능 + 제약 준수 → 플랜에 반영
       - 경미 반영: 소규모 → 한 줄 추가
       - 기각: 제약 위반 또는 비현실적 → 사유와 함께 기각 기록
       - 보류: 현재 scope 밖 → "향후 고려" 섹션에 기록

    4. 수정된 플랜 저장 → 버전업 (v1.0 → v1.1)
    5. 모든 판단을 플랜의 "리뷰 반영 이력" 부록에 기록
    6. 수렴 판단:
       - round 1: 신규 반영 5건 이상 → round 2 진행
       - round 2: 신규 반영 3건 이하 → 수렴
       - round 3: 신규 반영 0건 → 확정
       - 사용자에게 "추가 라운드 진행? (y/n)" 확인
    7. round += 1, version 업
```

### 3중 파일 수정 방지 메커니즘

Gemini가 과거에 "리뷰 요청"을 "개선 작업"으로 오인해 파일을 무단 생성/수정한 사고 기록이 있음 (예: Sidebar 수정 + Admin 대시보드 생성). 이를 방지하기 위해 3중 방어:

| 계층 | 방어 수단 | 역할 |
|---|---|---|
| 1. CLI 플래그 | `--approval-mode plan` | Gemini 자체 read-only 모드로 파일 수정 원천 차단 |
| 2. 프롬프트 강제 | "수정 금지, 리포트만 stdout 출력" 문구 | LLM 의도 수준에서 행동 제약 |
| 3. git-guard | 호출 전후 `git status --porcelain` 비교 | 앞선 2단계를 우회한 수정을 외부에서 감지 + rollback |

어느 한 층이 실패해도 나머지 층에서 잡아낼 수 있도록 설계.

### 디렉토리 구조

```
.claude/prompts/{플랜명}-{버전}/
├── input/                  ← Claude가 생성, `gemini -p`로 자동 호출
│   ├── A1_{topic}.md
│   ├── A2_{topic}.md
│   ├── B1_{topic}.md
│   └── C1_{topic}.md
└── output/                 ← Claude가 stdout 리다이렉트로 자동 저장 후 파싱
    ├── A1_{topic}.md
    └── B1_{topic}.md
```

---

## STAGE 4: /agent-team-planner (구현 계획 고도화)

리뷰 완료된 플랜으로 에이전트 팀을 설계합니다.

1. Skill 호출: `agent-team-planner` with 최종 플랜 파일
2. 산출물:
   - `.claude/agents/*_*.md` (에이전트 지침서)
   - `.claude/agents/team-manifest.json` (팀 구조 + 실행 그래프)
3. 사용자에게 팀 구성 요약 출력

---

## STAGE 5: /multi-agent-review (내부 2차 고도화)

에이전트 지침서 포함 구현 계획을 내부 교차검증합니다.

1. Skill 호출: `multi-agent-review` with 최종 플랜 파일
   - 동적 에이전트 배정 (CPA, 보안, 아키텍트, Devil 등)
   - 독립 리뷰 → 2라운드 토론 → 합의 보고서
2. RESOLVED 항목 자동 반영
3. ESCALATED 항목 사용자 판정
4. 구현 계획 + 지침서 업데이트

---

## STAGE 6: Gemini 외부 리뷰 (고도화된 플랜, 2-3회)

STAGE 3과 동일한 루프 구조. STAGE 5까지 고도화된 플랜을 대상으로 실행합니다.

### STAGE 3과의 차이점

| | STAGE 3 | STAGE 6 |
|---|---|---|
| 입력 | 플랜 초안 | 고도화된 플랜 + 에이전트 지침서 + team-manifest |
| 브리핑에 추가 | — | STAGE 5 내부 리뷰 결과 요약 (외부 모델이 내부 리뷰를 교차 확인) |
| 리뷰 유형 | Opus가 STAGE 3 시작 시 설계한 유형 재사용 | **Opus가 고도화 맥락에 맞게 유형 재설계 가능** (구현 실현성, 분업 타당성 등 관점 추가) |
| 디렉토리 | `.claude/prompts/{플랜명}-{버전}/` | 동일 (버전만 올라감) |

### 루프/프롬프트 생성 규칙

STAGE 3과 동일. 단, 공통 브리핑에 아래 추가 포함:
- 에이전트 팀 구조 요약 (team-manifest.json)
- STAGE 5 내부 리뷰 합의 보고서 요약
- "내부 리뷰에서 RESOLVED된 항목을 재검토하고, 놓친 부분을 지적해주세요"

---

## STAGE 7: 최종 플랜 확정

모든 리뷰를 종합하고 구현 시작 전 최종 확인합니다.

### 확정 체크리스트

아래 **모든 항목이 충족**되어야 STAGE 8로 진행:

- [ ] CRITICAL 미해결 0건
- [ ] 모든 Task에 `parallel` / `depends_on` 태그 존재
- [ ] 모든 Task에 검증 가능한 `완료 기준` 체크박스 존재
- [ ] ADR에 주요 설계 결정의 근거 + 기각된 대안이 기록됨
- [ ] 리스크 & 미결 사항 테이블에 High 항목이 해결 또는 수용됨

### 미충족 시 회귀 판단

| 미충족 유형 | 회귀 대상 |
|------------|----------|
| 기술적 결함 (구현 불가, 아키텍처 충돌) | STAGE 5 재실행 |
| 외부 리뷰 CRITICAL 미반영 | STAGE 6 재실행 |
| Task 구조/의존성 불명확 | STAGE 2에서 해당 Task 보완 |

### 확정 절차

1. 리뷰 반영 이력 부록 최종 정리 (반영/기각/보류 전체 목록)
2. 최종 플랜 저장 → `.claude/plans/{플랜명}_final.md`
3. 에이전트 지침서 최종 버전 저장
4. 사용자 최종 승인: "이 플랜으로 구현을 시작합니까? (y/n)"

---

## STAGE 8: 구현

1. `/plan-to-tasks` 호출 → 플랜의 PRD 태그(`parallel`, `depends_on`)를 파싱하여 태스크 생성 + 의존성 설정
2. 사용자에게 태스크 목록 + 실행 순서(wave) 확인
3. `/execute-plan` 호출 → wave별 병렬 실행 + 중간 검증
4. 완료 후 `/verify` 실행 (build + lint + format + test)

---

## STAGE 9: Evaluator 설계 + Auto-research 루프

구현 완료된 코드를 **객관적 지표로 자동 개선**합니다.
코드 리뷰(STAGE 10/11)에 진입하기 전에 기계적으로 최적화할 수 있는 부분을 먼저 처리합니다.

> **Layer 안내**: STAGE 8 (`/execute-plan`) 은 *의도적으로* 가벼운 lint 만 하고, 모든 무거운 verification (테스트 실행 포함) 은 STAGE 9 와 최종 `/verify` 로 위임된다. 이 분리가 forge 의 핵심 구조이며, STAGE 8 에 테스트 사이클을 박으면 그 분리가 깨진다 — race condition 이 아니라 **layer 위반** 이 이유.
>
> STAGE 9-4 의 auto-research 루프는 이미 `RED check (Gold fail) → minimal change → fresh score → commit-or-rollback` 사이클을 가지고 있다. 이는 외부 TDD 프레임워크가 아니라 *forge 자체* 의 검증 패턴이며, "출제자 ≠ 응시자" (9-2 의 Gold test 격리) 원칙으로 vanilla TDD 보다 더 강한 anti-gaming 을 제공한다.
>
> forge 의 3 개 discipline 스킬 (`test-driven-development`, `verification-before-completion`, `systematic-debugging`) 의 *고유한* STAGE 9 기여는 9-2 의 RED 입증 한 가지뿐 — Gold test 를 작성한 후 현재 코드에서 *실제로 fail 하는지* 확인하고, 통과한다면 폐기 후 재작성. 그 외의 9-4 단계는 이미 자체적으로 동등한 discipline 을 적용하고 있다.

### 9-1. Evaluator 동적 설계 (Opus)

프로젝트마다 평가 기준이 다르므로, Opus가 최종 플랜(STAGE 7 산출물)을 분석하여 evaluator를 설계합니다.

**잠금 규칙**: 기존 `eval_config.json`이 있으면 **재설계하지 않는다**. `--from 9` 재개 시 이전 세션의 config를 그대로 사용하여 점수 연속성을 보장.

**입력**: 최종 플랜 (`_final.md`) + 구현된 코드

**Opus가 결정하는 것**:

| 항목 | 설명 |
|------|------|
| 카테고리 | 이번 구현에 적합한 평가 관점 (예: 회계 정합성, API 보안, UI 접근성) |
| 가중치 | 카테고리별 비중 (합계 100%) |
| 개별 테스트 항목 | 플랜의 `완료 기준` 체크박스에서 파생 + Opus 자체 추가 |
| 채점 방식 | 항목별 binary / threshold / count 선택 |
| 목표 점수 | Auto-research 루프 종료 기준 (기본: 85점) |

**재사용 프레임워크** (고정, 수정 불필요):
- `framework/scorer.py` — binary/threshold/count 채점 엔진
- `framework/reporter.py` — HTML/JSON 리포트 생성
- `framework/types.py` — EvalMeta, EvalReport 데이터 구조

**Opus가 생성하는 것**:
- `evaluator/specs/test_*.py` (백엔드/CLI) 또는 `evaluator/specs/*.spec.ts` (프론트엔드)
- `evaluator/eval_config.json` — 카테고리, 가중치, 목표 점수

```json
{
  "plan": "{플랜명}_final.md",
  "target_score": 85,
  "max_iterations": 20,
  "categories": [
    { "id": "accounting-accuracy", "weight": 30, "description": "회계 처리 정합성" },
    { "id": "api-security", "weight": 25, "description": "인증/인가/입력 검증" },
    { "id": "performance", "weight": 20, "description": "쿼리 성능, 응답 시간" },
    { "id": "test-coverage", "weight": 15, "description": "핵심 경로 테스트 커버리지" },
    { "id": "ux-accessibility", "weight": 10, "description": "접근성, 반응형" }
  ]
}
```

### 9-2. Gold Test 설계 (별도 세션, Gaming 방지)

Auto-research 루프가 점수만 올리고 실제 품질은 안 올리는 **Evaluator gaming**을 방지하기 위해,
Evaluator specs와 **완전히 격리된 별도 Claude 세션**에서 Gold test를 설계합니다.

> **RED 입증 절차** (gap-closing test 에 적용):
>
> 1. Gold test 작성
> 2. **현재 코드 기반에서 그대로 실행** → 작성된 Gold test 가 *실제로 fail* 하는지 확인
> 3. **gap-closing test** (구현 안 된 동작을 검증) → fail 안 하면 폐기 후 재작성. 이 카테고리의 Gold test 는 RED 가 *필수*
> 4. **anchor test** (이미 잘 동작하는 걸 회귀 방지로 anchor) → 통과 OK. `tags: [anchor]` 같은 marker 로 명시. anchor 는 RED 강제 안 함
> 5. 두 카테고리 모두 정상 확인 후에만 `evaluator/gold/` 에 commit
>
> 이 분리는 vanilla TDD 보다 *더 강한* 입증이다. vanilla TDD 는 같은 사람이 RED→GREEN 둘 다 보지만, 9-2 의 Gold test 는 *Auto-research 가 GREEN 을 낼 때까지 직접 보지 못하는* 검증 명령이다. 출제자/응시자 분리 + (gap-closing 의 경우) RED 입증의 결합.

**원칙: 출제자 ≠ 응시자**
- Gold test 세션은 Auto-research 루프와 컨텍스트를 공유하지 않음
- Gold test는 **읽기 전용** — Auto-research 루프가 수정 불가

**커버리지: 전체 ISS 시나리오**
- 플랜의 모든 `완료 기준` 체크박스를 gold test로 변환
- 정상 시나리오 + 엣지 케이스 + 실패 시나리오 전부 포함

**Gold test vs Evaluator specs 분리**:

```
evaluator/
├── specs/              ← Opus 생성 (Auto-research가 점수 올리는 대상)
│   └── test_*.py
├── gold/               ← 별도 세션 생성 (수정 금지, CI 차단)
│   └── test_gold_*.py
└── eval_config.json
```

**CI 차단**: Gold test 실패 시 Auto-research 루프 **즉시 중단**. 점수 85 도달과 무관하게 gold test 전체 통과 필수.

### 9-3. Evaluator 초회 실행

1. 생성된 evaluator specs + gold tests 실행
2. 초기 점수 측정 + 리포트 생성 (`eval-report.html`, `eval-report.json`)
3. 결과 출력:
   ```
   === STAGE 9: Evaluator 초기 점수 ===
   종합: 72/100 (목표: 85)
   Gold test: 18/23 PASS (5 FAIL — CI 차단 활성)
   - accounting-accuracy: 80 (30%)
   - api-security: 65 (25%)
   - performance: 70 (20%)
   - test-coverage: 68 (15%)
   - ux-accessibility: 75 (10%)
   ```

### 9-4. Auto-research 루프

초기 점수가 목표 미달 시 자동 개선 루프를 실행합니다.

**Git 안전장치**: 루프 시작 전 `git tag eval-baseline-{timestamp}` 생성. 루프 전체 실패 시 `git reset --hard eval-baseline-{tag}` 로 완전 복원.

```
iteration = 1
while score < target_score AND iteration <= max_iterations:
    1. Gold test 전체 통과 확인 (실패 시 해당 항목 우선 수정)
    2. 최저 점수 카테고리 식별
    3. 해당 카테고리의 실패/저점 항목 분석 (어느 spec, 어느 입력, 어느 layer 에서 깨지는지 evidence 부터)
    4. 코드 수정 (한 번에 하나의 개선에 집중)
    5. `/verify` 실행 (기존 테스트 깨뜨리지 않는지 확인)
    6. Gold test 재실행 (1건이라도 실패 → 즉시 rollback)
    7. Evaluator 재실행 → 새 점수 측정
    8. 판단:
       - 점수 개선 + Gold 전체 PASS → git commit "eval: {카테고리} {이전}→{이후}점" → 유지
       - 점수 악화 또는 Gold 실패 → git restore --staged . && git restore . && git clean -fd → rollback
    9. iteration += 1
```

> 위 루프는 forge 의 *기존* 검증 사이클이며 외부 TDD 스킬 없이도 RED check (step 6 의 Gold fail = 즉시 rollback), fresh evidence (step 7 의 새 점수 측정), commit/rollback 판정 (step 8) 을 모두 자체적으로 수행한다. 3 개 discipline 스킬은 step 3 의 분석이나 step 4 의 수정을 *원리적으로 안내* 할 수 있지만 9-4 의 실행 흐름을 바꾸지는 않는다.

### 루프 종료 조건

| 조건 | 처리 |
|------|------|
| `score >= target_score` + Gold 전체 PASS | 성공 — STAGE 10으로 진행 |
| `iteration > max_iterations` | 한계 도달 — 현재 최고 점수로 STAGE 10 진행, 미달 항목 목록을 코드 리뷰어에게 전달 |
| 3회 연속 rollback | 자동 개선 한계 — 같은 수정 패턴이 계속 새 곳에서 깨진다는 신호. 수정 자체가 아니라 *수정이 박히는 자리* 가 잘못됐을 가능성. 루프 종료, 사용자에게 수동 개입 요청 |
| Gold test 실패 + 3회 수정 실패 | Gold 차단 — Gold 가 가리키는 동작이 현재 아키텍처에서 표현 불가능할 수 있음. 사용자에게 수동 개입 요청 (실패 항목 + 파일:라인 제시) |

### 수동 개입 요청 시 표준 출력

```
=== STAGE 9: 수동 개입 요청 ===
사유: 3회 연속 rollback (카테고리: api-security)
현재 점수: 68 / 목표: 85
Gold test: 21/23 PASS
실패 항목:
  - [GOLD-SEC-03] JWT 만료 검증 누락 (파일: auth/service.py:142)
  - [GOLD-SEC-07] 쿼리 파라미터 미검증 (파일: api/router.py:89)
권장 액션: 위 파일을 직접 수정 후 /pipeline --from 9 로 재개
```

### 산출물

- `evaluator/eval_config.json` — 평가 설정 (잠금: 재개 시 재설계 금지)
- `evaluator/specs/test_*.py` 또는 `*.spec.ts` — Evaluator 항목 (Opus 생성)
- `evaluator/gold/test_gold_*.py` 또는 `*.spec.ts` — Gold test (별도 세션 생성, 수정 금지)
- `evaluator/reports/eval-report.html` — 최종 리포트
- `evaluator/reports/eval-report.json` — 기계 파싱용 결과
- Auto-research 이력: git log에 `eval:` 접두사 커밋으로 추적
- 안전장치: `eval-baseline-{timestamp}` git 태그

---

## STAGE 10: /multi-agent-codereview (내부 코드 리뷰 + 1차 수정)

구현 완료된 코드를 내부 교차검증합니다.

1. Skill 호출: `multi-agent-codereview` with "최근 변경사항" 또는 변경 파일 목록
   - 동적 에이전트 배정 (기술 + 실무 관점)
   - 독립 코드 리뷰 → 2라운드 토론 → 합의
   - **STAGE 9 Evaluator 리포트를 리뷰 컨텍스트에 포함** (미달 항목에 집중)
2. 권고 액션 아이템 중 "즉시수정" 항목 자동 반영
3. "다음스프린트" / "향후검토" 항목은 목록 제시
4. 수정 후 `/verify` 재실행

---

## STAGE 11: Codex 외부 코드 리뷰 (자동, 최대 3회)

구현된 코드를 OpenAI Codex(GPT)로 독립 교차검증합니다.
STAGE 10(내부 Claude 리뷰)과 **다른 모델의 시각**으로 블라인드스팟을 포착하는 것이 목적입니다.
사용자 개입 없이 자동 실행됩니다.

### 11-1. Standard Review

`/codex:review` 실행 — git 변경사항 기반 표준 코드 리뷰.

```
codex:review --scope branch --wait
```

- `--scope branch`: 현재 브랜치 전체 변경사항 리뷰 (STAGE 8 구현분 전체)
- `--wait`: 결과가 나올 때까지 동기 대기
- 산출물: Codex stdout (findings 목록 + severity + file:line)

### 11-2. Adversarial Review

`/codex:adversarial-review` 실행 — 설계 선택, 트레이드오프, 가정에 도전.

```
codex:adversarial-review --scope branch --wait
```

STAGE 9 Evaluator에서 미달인 카테고리가 있으면 focus 텍스트로 전달:
```
codex:adversarial-review --scope branch --wait "Evaluator 미달 카테고리: {카테고리명} ({점수}/{목표})"
```

### 11-3. 결과 통합 + 수정 루프

```
round = 1
while round <= 3:
    1. Standard Review + Adversarial Review 결과 수집
    2. Opus가 결과 파싱 + 분류:
       - 반영: 유의적 + 실현 가능 + STAGE 10 합의와 비충돌 → 코드 수정
       - 기각: STAGE 10에서 이미 RESOLVED된 항목의 재지적 → 사유 기록 후 무시
       - 보류: 현재 scope 밖 → "향후 고려" 기록
    3. "반영" 항목 수정 → `/verify` 재실행
    4. 수렴 판단:
       - round 1: Critical/Major 반영 2건 이상 → round 2 진행
       - round 2: Critical/Major 반영 0건 → 수렴
       - round 3: 무조건 종료
    5. round += 1
```

### STAGE 10 vs STAGE 11 역할 분담

| | STAGE 10 (내부) | STAGE 11 (외부) |
|---|---|---|
| 모델 | Claude (Sonnet 서브에이전트) | Codex (GPT) |
| 방식 | 다중 에이전트 토론 (2라운드) | Standard + Adversarial 리뷰 |
| 관점 | 기술 + 실무 도메인 혼합 | 코드 품질 + 설계 도전 |
| 자동화 | 자동 | 자동 (수동 핸드오프 없음) |
| 비용 | Sonnet x N 에이전트 | Codex API 호출 |

### Codex 리뷰 결과 처리 규칙

1. **Codex 결과는 있는 그대로 출력** — Claude가 요약/축약하지 않음 (codex-result-handling 스킬 준수)
2. **자동 수정 금지** — findings 표시 후 사용자에게 수정 범위 확인
3. **STAGE 10과 충돌하는 지적**: STAGE 10 RESOLVED가 우선, 단 Codex가 새로운 근거를 제시한 경우 사용자 판단 요청
4. **Critical 발견 시**: 즉시 루프 중단 + 사용자에게 수동 개입 표준 출력

---

## STAGE 12: Ship

1. `/verify` 최종 실행 (전체 통과 확인)
   - **CRITICAL**: pytest는 반드시 Docker DB (`make db-up`) 기동 상태에서 실행
   - Docker 미기동 상태에서 push하면 CI 실패 → 불필요한 수정 루프 발생
2. `/ship` 호출:
   - 파일 스테이징 (사용자 확인)
   - 커밋 메시지 자동 생성
   - 푸시
   - CI 추적
   - CI 실패 시 자동 수정 루프
3. `/session-save` 호출

---

## 상태 관리

### 중단/재개
- 어떤 STAGE에서든 "중단" → `.claude/sessions/STATE.md`에 현재 상태 저장
- 다음 세션에서 `/pipeline --from N` 으로 재개

### STATE.md 템플릿

```markdown
# Pipeline State

## 현재 상태
- **STAGE**: 9
- **플랜명**: client-onboarding
- **중단 시각**: 2026-03-29T14:30:00+09:00
- **중단 사유**: 컨텍스트 한계 / 사용자 요청 / 외부 리뷰 대기

## 산출물 경로
- 최종 플랜: `.claude/plans/client-onboarding_final.md`
- 에이전트 지침서: `.claude/agents/`
- team-manifest: `.claude/agents/team-manifest.json`
- Gemini 프롬프트: `.claude/prompts/client-onboarding-v1.2/`
- Evaluator 설정: `evaluator/eval_config.json`
- Evaluator 리포트: `evaluator/reports/eval-report.json`

## 진행 요약
- STAGE 1-7: 완료
- STAGE 8: 완료 (Task 12/12)
- STAGE 9: 진행 중 — iteration 8/20, 현재 점수 79/85
- STAGE 10-12: 미시작

## 다음 액션
- `/pipeline --from 9` 로 재개
- Auto-research 루프 iteration 9부터 계속
```

### 파일 구조

```
.claude/
├── plans/
│   ├── {플랜명}_draft.md          ← STAGE 2 초안
│   ├── {플랜명}_v1.0.md           ← STAGE 3 리뷰 시작 버전
│   ├── {플랜명}_v1.1.md           ← STAGE 3 리뷰 반영 후
│   ├── {플랜명}_refined.md        ← STAGE 5 후
│   └── {플랜명}_final.md          ← STAGE 7 최종 확정
├── agents/
│   ├── *_*.md                     ← STAGE 4 에이전트 지침서
│   └── team-manifest.json         ← STAGE 4 팀 구조
├── prompts/
│   ├── {플랜명}-briefing.md       ← STAGE 2b Gemini 브리핑
│   ├── {플랜명}-v1.0/             ← STAGE 3 ABC 리뷰
│   │   ├── input/
│   │   └── output/
│   ├── {플랜명}-v1.2/             ← STAGE 6 ABC 리뷰 (버전업)
│   │   ├── input/
│   │   └── output/
│   └── {플랜명}-code-v1.0/        ← STAGE 11 ABC 코드 리뷰
│       ├── input/
│       └── output/
├── sessions/
│   └── STATE.md                   ← 중단/재개용
└── evaluator/ (또는 프로젝트 루트의 evaluator/)
    ├── eval_config.json           ← STAGE 9 Opus 설계
    ├── specs/                     ← STAGE 9 Opus 생성 테스트
    └── reports/                   ← STAGE 9 리포트
```

### STAGE 간 데이터 전달 경로

`--from N` 재개 시 이전 산출물을 빠르게 찾기 위한 참조표.

```
STAGE 2  ─── {플랜명}_draft.md (PRD 태그 + 완료 기준) ──→ STAGE 3 입력
STAGE 3  ─── {플랜명}_v{N}.md (리뷰 반영 버전) ──────────→ STAGE 4 입력
STAGE 4  ─── agents/*.md + team-manifest.json ──────────→ STAGE 5 입력
STAGE 5  ─── {플랜명}_refined.md + 합의 보고서 ─────────→ STAGE 6 입력
STAGE 6  ─── {플랜명}_v{N}.md (2차 리뷰 반영) ──────────→ STAGE 7 입력
STAGE 7  ─── {플랜명}_final.md ─────────────────────────→ STAGE 8, 9 입력
STAGE 8  ─── 구현된 코드 (git) ─────────────────────────→ STAGE 9 입력
STAGE 9  ─── eval_config.json + eval-report.json ───────→ STAGE 10, 11 입력
STAGE 10 ─── 합의 보고서 + 수정 코드 ──────────────────→ STAGE 11 입력 (Codex 자동)
STAGE 11 ─── Codex 리뷰 반영 수정 코드 ────────────────→ STAGE 12 입력
```

### 보안 게이트

- **STAGE 3/6 → 다음 단계 진행 전**: CRITICAL 미해결 0건 필수
- **STAGE 11 → STAGE 12**: Codex Critical 발견 0건 필수 (Critical 발견 시 수정 후 재리뷰)
- **STAGE 7 → STAGE 8**: 사용자 명시적 승인 필수 + 확정 체크리스트 전항 충족
- **STAGE 9 → STAGE 10**: Evaluator 목표 점수 도달 + Gold test 전체 PASS (또는 max_iterations 소진)
- **STAGE 12**: `/verify` 전체 통과 필수

### 실패 등급별 회복 절차

| 실패 등급 | 예시 | 회복 방법 |
|----------|------|----------|
| **경미** | 단일 테스트 실패, lint 경고 | 해당 STAGE에서 수정 후 계속 진행 |
| **중간** | STAGE 9 Auto-research 3회 연속 rollback, STAGE 10 ESCALATED 다수 | 사용자에게 수동 개입 표준 출력 → 수정 후 `--from N`으로 재개 |
| **심각** | git 상태 오염, eval_config 손상, 산출물 누락 | `git reset --hard eval-baseline-{tag}`로 STAGE 9 시작점 복원, 또는 `--from {이전 STAGE}`로 회귀 |
| **치명** | 잘못된 코드가 이미 push됨 | `git revert`으로 롤백 커밋 생성 → `/pipeline --from 8`로 구현부터 재시작 |

**회복 책임**: Claude가 자동 감지 가능한 실패(테스트, lint, Gold test)는 자동 회복. 판단이 필요한 실패(ESCALATED, 비즈니스 로직 오류)는 사용자에게 위임.
