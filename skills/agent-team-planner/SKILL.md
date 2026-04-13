---

name: agent-team-planner
description: >
  프로젝트 플랜/PRD를 분석하여 에이전트 팀을 설계하고 각 에이전트에 스킬·페르소나·작업 지침서를
  배정하는 사전 오케스트레이션 플래너. multi-agent-orchestration의 실행 전 단계로,
  플랜의 각 영역에 최적의 에이전트 구성을 결정한다.
  트리거: "에이전트 팀 구성", "팀 빌딩", "에이전트 배치", "작업 지침서 작성",
  "플랜에 에이전트 배정", "팀 설계", "워커 구성", 또는 프로젝트 플랜을 기반으로
  멀티에이전트 워크플로우를 새로 설계할 때.
effort: high
---

# Agent Team Planner

프로젝트 플랜 → 도메인 분해 → 에이전트/팀 배치 → 스킬·페르소나 배정 → 작업 지침서 생성.
`multi-agent-orchestration` 스킬의 **사전 단계**로, 실행 전에 팀 구조를 명확화한다.

## 워크플로우

```
PHASE 1  Plan Analysis ──────── PRD/플랜 읽기 → 도메인·태스크 목록 추출
    │
PHASE 2  Complexity Assessment ─ 각 도메인별 복잡도 판정 → 단일/팀 결정
    │
PHASE 3  Skill Inventory ────── 설치된 스킬 스캔 → 도메인-스킬 매칭
    │
PHASE 4  Persona & Directive ── 에이전트별 페르소나·제약·산출물 정의 → 지침서 생성
    │
PHASE 5  Execution Graph ────── 의존성 분석 → 병렬/순차 실행 순서 확정
    │
OUTPUT   .claude/agents/ 에 작업 지침서 파일 생성 + team-manifest.json
```

---

## PHASE 1: Plan Analysis

PRD 또는 프로젝트 플랜 파일을 읽고 도메인·태스크 목록을 추출한다.

1. 사용자로부터 플랜 파일 경로를 받는다 (PRD.md, CLAUDE.md, 또는 자유 텍스트)
2. 플랜을 읽고 아래 구조로 분해한다:

```json
{
  "project_name": "프로젝트명",
  "domains": [
    {
      "id": "D1",
      "name": "도메인명",
      "tasks": [
        {"id": "T1.1", "description": "태스크 설명", "inputs": [], "outputs": []}
      ]
    }
  ]
}
```

3. 도메인 분류 기준:
   - **기능 경계**: 서로 다른 입력/출력을 가진 작업 그룹
   - **전문성 경계**: 다른 스킬셋이 필요한 작업 그룹
   - **데이터 경계**: 서로 다른 데이터를 처리하는 작업 그룹

---

## PHASE 2: Complexity Assessment

각 도메인의 복잡도를 판정하여 에이전트 구성 방식을 결정한다.

### 복잡도 판정 매트릭스

| 차원 | 낮음 (1) | 중간 (2) | 높음 (3) |
|------|---------|---------|---------|
| 태스크 수 | 1-2개 | 3-5개 | 6개+ |
| 데이터 볼륨 | 단일 파일 | 복수 파일 | 대량 배치 |
| 판단 복잡도 | 규칙 기반 | 규칙+예외 | 전문가 판단 필요 |
| 스킬 다양성 | 단일 스킬 | 2-3 스킬 | 4+ 스킬 |
| 외부 의존성 | 없음 | API 1-2개 | MCP+API+사용자 입력 |

### 복잡도 → 에이전트 구성 매핑

| 총점 | 구성 | 패턴 |
|------|------|------|
| 5-7 | **단일 에이전트** | Sonnet 워커 1명 |
| 8-10 | **소규모 팀** | Opus 리드 + Sonnet 워커 1-2명 |
| 11-13 | **전문 팀** | Opus 오케스트레이터 + 전문 Sonnet 워커 3-4명 |
| 14-15 | **대규모 팀** | Opus 오케스트레이터 + 도메인별 Sonnet 팀 + 검증 에이전트 |

---

## PHASE 3: Skill Inventory

설치된 스킬을 스캔하고 각 도메인에 매칭한다.

### 스킬 스캔

`scripts/scan_skills.py`를 실행하여 설치된 스킬 인벤토리를 획득한다:

```bash
python .claude/skills/agent-team-planner/scripts/scan_skills.py
```

출력: 스킬명, 설명, 스크립트 목록이 포함된 JSON 배열.

### 스킬-도메인 매칭 규칙

1. 각 도메인의 태스크를 순회하면서 필요한 능력을 식별
2. 스킬 인벤토리에서 해당 능력과 매칭되는 스킬을 선택
3. 매칭 결과를 도메인별로 정리:

```json
{
  "domain_id": "D1",
  "assigned_skills": ["file-reader", "report-builder"],
  "required_tools": ["Read", "Write", "Bash"],
  "mcp_tools": []
}
```

### 스킬 분류 체계

| 카테고리 | 해당 스킬 | 용도 |
|---------|----------|------|
| 파싱 | file-reader, document-parser, excel-parser, raw-parser | 입력 데이터 추출 |
| 계산 | tax-calculator | 결정론적 산출 |
| 매핑 | data-mapper, column-mapper, rule-extraction | 항목 매칭·변환 |
| 출력 | report-builder, output-builder, excel-generator, word-handler | 산출물 생성 |
| 검증 | verification-loop, validator, validation, field-validator | 정합성 확인 |
| 인프라 | content-hash-cache, continuous-learning-v2 | 캐싱·학습 |
| 외부 | 공시가격, 등기부-발급 | MCP/API 연동 |

---

## PHASE 4: Persona & Directive Generation

각 에이전트에 페르소나·스킬·제약을 배정하고 작업 지침서를 생성한다.

### 에이전트 유형별 페르소나

페르소나 템플릿은 [references/directive-schema.md](references/directive-schema.md) 참조.

#### 오케스트레이터 (Opus)

```yaml
role: orchestrator
model: opus
responsibilities:
  - 워크플로우 분기 결정
  - 워커 결과 교차검증
  - 사용자 대화 (에스컬레이션)
  - 규칙/지식 베이스 업데이트
  - MCP 도구 호출
constraints:
  - 대용량 파일 직접 파싱 금지 (Sonnet 위임)
  - 기계적 반복 작업 직접 수행 금지
escalation: 사용자에게 직접 확인
```

#### 전문 워커 (Sonnet)

```yaml
role: specialist-worker
model: sonnet
responsibilities:
  - 할당된 도메인의 태스크 실행
  - 지침서에 명시된 스킬/스크립트 사용
  - JSON 체크포인트 산출
constraints:
  - 할당된 스킬 외 작업 금지
  - 사용자 대화 불가
  - MCP 도구 접근 불가
  - 다른 워커와 직접 통신 금지
escalation: Opus 오케스트레이터에게 보고 (JSON 결과에 confidence: low 표시)
```

#### 검증 에이전트 (Opus 또는 Sonnet)

```yaml
role: verifier
model: opus  # 논리적 정합성 검증 시
responsibilities:
  - 워커 산출물의 정합성 검증
  - 교차검증 (복수 워커 결과 비교)
  - 검증 실패 시 원인 분석
constraints:
  - 데이터 수정 불가 (검증만)
  - 검증 결과만 보고
escalation: 검증 실패 → Opus 오케스트레이터
```

### 작업 지침서 생성 규칙

각 에이전트/팀에 대해 `.claude/agents/` 디렉토리에 지침서를 생성한다.

**파일명 규칙**: `{project}_{step/role}_{function}.md`
- 예: `cgt_step1_transfer-parser.md`
- 예: `barogo_worker_hub-extractor.md`

**지침서 필수 포함 요소** — 스키마 상세는 [references/directive-schema.md](references/directive-schema.md) 참조:

1. **헤더**: 에이전트 ID, 역할, 모델
2. **페르소나**: 전문성, 행동 원칙
3. **입력**: 필요한 파일/데이터 경로
4. **스킬**: 사용할 스킬 목록 + Read 지시
5. **태스크**: 수행할 작업 (번호 순서)
6. **산출물**: 출력 파일명, JSON 스키마
7. **제약**: 금지 사항, 범위 제한
8. **에스컬레이션**: 판단 불확실 시 처리 방법
9. **검증**: 자기 검증 체크리스트

---

## PHASE 5: Execution Graph

에이전트 간 의존성을 분석하고 실행 순서를 확정한다.

### 의존성 분석

```
각 에이전트의 inputs/outputs를 매칭:
  Agent A outputs → Agent B inputs  ⟹  A → B (순차)
  Agent A outputs ∩ Agent B inputs = ∅  ⟹  A ‖ B (병렬 가능)
```

### 실행 그래프 패턴 — 상세는 [references/team-patterns.md](references/team-patterns.md) 참조

| 패턴 | 구조 | 적용 조건 |
|------|------|----------|
| Pipeline | A → B → C | 각 단계가 이전 산출물 의존 |
| Fan-out/Fan-in | A → [B1‖B2‖B3] → C | 동일 구조 반복, 독립 입력 |
| Hub-spoke | Opus → [W1‖W2‖W3] → Opus | Opus가 배분+통합 |
| Conditional | A → (조건) → B or C | 분기 필요 |

### team-manifest.json 생성

최종 산출물로 `{project}/.claude/agents/team-manifest.json`을 생성한다:

```json
{
  "project": "프로젝트명",
  "created": "2026-03-09",
  "topology": "hub-spoke",
  "agents": [
    {
      "id": "orchestrator",
      "role": "orchestrator",
      "model": "opus",
      "directive": ".claude/agents/{project}_orchestrator.md"
    },
    {
      "id": "worker-1",
      "role": "specialist-worker",
      "model": "sonnet",
      "directive": ".claude/agents/{project}_step1_parser.md",
      "skills": ["file-reader", "document-parser"],
      "depends_on": [],
      "parallel_with": ["worker-2"]
    }
  ],
  "execution_order": [
    {"phase": 1, "agents": ["orchestrator"], "mode": "sequential"},
    {"phase": 2, "agents": ["worker-1", "worker-2"], "mode": "parallel"},
    {"phase": 3, "agents": ["verifier"], "mode": "sequential"}
  ],
  "checkpoints": [
    "step1_result.json",
    "step2_result.json"
  ]
}
```

---

## 산출물 요약

| 산출물 | 위치 | 용도 |
|--------|------|------|
| 에이전트 지침서 (N개) | `{project}/.claude/agents/*.md` | 각 워커의 작업 지시 |
| team-manifest.json | `{project}/.claude/agents/team-manifest.json` | 팀 구조·의존성·실행 순서 |
| 스킬 인벤토리 | (인메모리) | PHASE 3 중간 산출물 |

---

## 기존 프로젝트 참조 패턴

| 프로젝트 | 토폴로지 | 에이전트 수 | 에이전트 디렉토리 |
|---------|---------|-----------|----------------|
| 양도소득세 | Pipeline + 병렬(STEP 1‖3) | Opus 1 + Sonnet 7 | `세무/양도소득세/.claude/agents/` |
| 통합고용세액공제 | Sequential pipeline | Opus 1 + Sonnet 7 | `세무/통합고용세액공제/.claude/agents/` |
| 바로고 | Hub-spoke (허브별 병렬) | Opus 1 + Sonnet 4 | 모놀리식 (`pipeline.py`) |
| 주식평가보고서 | Sequential + 서브에이전트 | Opus 1 (mapper 내재) + Sonnet 2 | `평가/주식평가보고서/.claude/agents/mapper/` |

새 프로젝트 설계 시 가장 유사한 기존 패턴을 참조하여 일관성을 유지한다.
