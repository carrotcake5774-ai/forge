# 🔨 Forge

> **12-STAGE plan-to-ship pipeline for Claude Code**
> Multi-agent orchestration with Claude + Codex CLI

Forge는 아이디어에서 배포까지의 전체 개발 사이클을 12개 STAGE로 구조화한 Claude Code 플러그인입니다. 단일 모델의 편향을 피하기 위해 **Claude (Anthropic) + Codex (OpenAI)** 두 모델을 각 역할에 배치해 교차검증하는 것이 핵심 철학입니다. v1.1.0부터 플랜 리뷰(STAGE 3/6)와 코드 리뷰(STAGE 11) 모두 Codex CLI를 사용합니다 (v1.0.x는 플랜 리뷰에 Gemini CLI 사용).

---

## 왜 Forge인가

- **멀티모델 블라인드스팟 탐지** — 플랜과 코드 모두 다른 모델(Codex)로 외부 리뷰하는 게이트가 3곳 (STAGE 3, 6, 11)
- **CRITICAL 0건 하드 게이트** — 외부 리뷰에서 Critical 이슈가 남으면 다음 단계로 진행 불가
- **Fast/Full Track 자동 분기** — 복잡도에 따라 5단계(Fast) 또는 12단계(Full)로 경로 압축
- **Evaluator 자동 연구 루프** (STAGE 9) — 코드 리뷰 전에 기계적으로 최적화 가능한 항목을 먼저 처리
- **3중 파일 수정 방지** — Codex CLI `-s read-only` 샌드박스(macOS Seatbelt 기반 OS-level) + 프롬프트 강제 + git-guard로 무단 수정 차단

---

## 설치

### 로컬 개발 (즉시 사용)

```bash
git clone https://github.com/carrotcake5774-ai/forge
cd your-project
claude --plugin-dir /path/to/forge
```

### 마켓플레이스 방식 (영구 설치)

Claude Code 내부에서:
```
/plugin marketplace add carrotcake5774-ai/forge
/plugin install forge@forge
```

---

## 요구사항

Forge가 완전히 작동하려면 아래 외부 CLI가 필요합니다:

| 도구 | 용도 | 설치 |
|---|---|---|
| [Claude Code](https://claude.com/claude-code) | 전체 오케스트레이션 | 공식 사이트 |
| [Codex CLI](https://github.com/openai/codex) | STAGE 2b/3/6 외부 플랜 리뷰 + STAGE 11 외부 코드 리뷰 | 공식 가이드 참조 |
| `git` | 모든 STAGE | 기본 설치 |

Codex CLI 없이 사용 시 `--skip-external` 플래그로 STAGE 3/6/11이 자동 스킵되고 내부 리뷰(STAGE 5/10)로 대체됩니다.

---

## 사용법

```bash
cd your-project
claude  # 플러그인이 마켓플레이스로 설치된 경우
# 또는
claude --plugin-dir /path/to/forge  # 로컬 경로 방식
```

Claude Code 프롬프트에서:

```
/forge:pipeline
```

이후 Forge가 STAGE 1부터 순차적으로 진행합니다. 재개 필요 시:

```
/forge:pipeline --from 5
```

### 제공 커맨드 (6종)

| 커맨드 | 역할 |
|---|---|
| `/forge:pipeline` | 12-STAGE 전체 파이프라인 오케스트레이션 |
| `/forge:plan-to-tasks` | PRD 플랜을 실행 가능 Task 목록으로 분해 |
| `/forge:execute-plan` | Task 목록을 병렬/순차 실행 |
| `/forge:verify` | 전체 검증 파이프라인 (lint, test, build) |
| `/forge:ship` | 커밋 + 푸시 + CI 추적 + 자동 수정 루프 |
| `/forge:session-save` | 세션 상태 저장 |

### 내장 스킬 (3종)

| 스킬 | 호출 시점 |
|---|---|
| `agent-team-planner` | STAGE 4 — 플랜에 맞는 에이전트 팀 설계 |
| `multi-agent-review` | STAGE 5 — 플랜을 다수 에이전트가 독립 리뷰 후 토론 |
| `multi-agent-codereview` | STAGE 10 — 구현된 코드를 다수 에이전트가 리뷰 |

---

## 12-STAGE 개요

### 📝 플랜 빌드 (STAGE 1~7)

| # | STAGE | 역할 |
|---|---|---|
| 1 | 아이디어 평가 | 적용 여부 판단 + 복잡도 분기 |
| 2 | 플랜 초안 작성 | PRD 형식, 소규모는 Claude 단독 / 대규모는 Codex 초안 경유 |
| 3 | **Codex 외부 리뷰** | 초안 대상 ABC 다중 유형 리뷰 (2-3회 루프) |
| 4 | 에이전트 팀 설계 | 플랜에 맞는 워커 에이전트 구성 |
| 5 | 내부 다중 리뷰 | Claude 서브에이전트들의 독립 리뷰 + 토론 |
| 6 | **Codex 외부 리뷰 2차** | 고도화된 플랜 대상 재리뷰 |
| 7 | 최종 플랜 확정 | CRITICAL 0건 + 사용자 승인 |

### 🔨 구현 (STAGE 8~9)

| # | STAGE | 역할 |
|---|---|---|
| 8 | 구현 | plan-to-tasks → execute-plan |
| 9 | **Evaluator 자동 루프** | 기계적 최적화 가능 항목 iteration 기반 해결 |

### 🔍 리뷰 & 배포 (STAGE 10~12)

| # | STAGE | 역할 |
|---|---|---|
| 10 | 내부 코드 리뷰 | 다수 에이전트의 토론 기반 리뷰 + 수정 |
| 11 | **Codex 외부 코드 리뷰** | Standard + Adversarial 자동 2-3회 |
| 12 | Verify + Ship | 최종 검증 → 커밋 → 푸시 → CI 추적 |

### 경로 분기

```
Fast Track (Low 복잡도):
  1 → 2a → 5 → 8 → 9 → 10 → 12     (5단계)

Full Track (Medium/High 복잡도):
  1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12     (12단계)
```

STAGE 1의 복잡도 판정(변경 파일 수, 아키텍처 변경 여부, 신규 모듈 유무)에 따라 자동 선택됩니다.

---

## 3중 파일 수정 방지 메커니즘

외부 LLM이 "리뷰 요청"을 "구현 작업"으로 오인해 파일을 무단 생성/수정할 위험을 방지하기 위해 Forge는 3중 방어를 구조화했습니다 (v1.0.x Gemini `--approval-mode plan` 시절부터 유지):

| 계층 | 방어 수단 | 역할 |
|---|---|---|
| 1. CLI 샌드박스 | `codex exec -s read-only` | macOS Seatbelt 기반 OS-level 읽기 전용 샌드박스. kernel이 파일쓰기를 차단 |
| 2. 프롬프트 강제 | "수정 금지, 리포트는 `-o` 파일로만 출력" 문구 | LLM 의도 수준 제약 |
| 3. git-guard | 호출 전후 `git status --porcelain` 비교 | 1, 2를 우회한 수정 감지 + rollback |

---

## 디렉토리 구조

```
forge/
├── .claude-plugin/
│   └── plugin.json           # 플러그인 매니페스트
├── commands/                 # 슬래시 커맨드 6종
│   ├── pipeline.md
│   ├── plan-to-tasks.md
│   ├── execute-plan.md
│   ├── verify.md
│   ├── ship.md
│   └── session-save.md
├── skills/                   # 내장 스킬 3종
│   ├── agent-team-planner/
│   ├── multi-agent-review/
│   └── multi-agent-codereview/
└── docs/
    └── plan_build_process_with_gem.md  # Gemini 시절 플랜 빌드 프로세스 (deprecated, 히스토리 보존)
```

---

## 프로젝트 적용

Forge는 특정 프로젝트/언어에 종속되지 않습니다. 호스트 프로젝트의 `CLAUDE.md`를 런타임에 읽어 그 안의 **IMMUTABLE CONSTRAINTS (DO NOT 규칙)**를 각 STAGE의 가이드레일로 사용합니다.

따라서 사용 전 호스트 프로젝트에 `CLAUDE.md`를 준비하는 것을 권장합니다. 예시 섹션:

```markdown
## DO NOT Rules

- DO NOT use FLOAT for monetary values. Always use NUMERIC(18,2).
- DO NOT skip migration when adding/modifying models.
- DO NOT commit .env files or any credentials.
```

---

## 라이선스

[MIT License](./LICENSE) © 2026 Glen

---

## 크레딧

Forge는 Claude Code × Codex CLI 협업 프로세스에서 파생된 파이프라인입니다. 외부 리뷰 워크플로우의 영감은 초기 Claude × Gemini ABC 리뷰 패턴 (v1.0.x)과 Codex 외부 검증 경험에서 비롯됐습니다. v1.1.0부터 플랜 리뷰도 Codex로 통합되어 외부 CLI 단일화를 달성.
