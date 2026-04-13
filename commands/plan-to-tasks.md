# /plan-to-tasks — 플랜 문서에서 태스크 자동 생성

구조화된 플랜 문서를 파싱하여 TaskCreate로 태스크를 자동 생성하고, 의존성을 설정합니다.

## 인자

- `$ARGUMENTS`: 플랜 소스. 다음 중 하나:
  - 파일 경로 (예: `.claude/plans/my-plan.md`)
  - `clipboard` — 사용자가 붙여넣은 플랜 텍스트를 파싱
  - 비어있으면 — 가장 최근 `.claude/plans/*.md` 파일 사용

## 파싱 규칙

플랜 문서에서 다음 패턴을 인식:

### 1. Phase/Sprint 구조
```markdown
## Phase 0: 긴급 수정
### 0-1. [CRITICAL] 제목
### 0-2. [MAJOR] 제목
## Phase A: 병렬 작업 (Bravo ‖ Delta ‖ Echo)
```
→ Phase별 태스크 그룹 생성, `[CRITICAL]`/`[MAJOR]` 태그로 우선순위 표시

### 2. 실행 그래프
```markdown
Phase 0 → Phase A [병렬] → Phase B → Phase C
```
→ 의존성(blockedBy) 자동 설정

### 3. 파일 변경 테이블
```markdown
| 파일 | 변경 |
|------|------|
| `component.tsx` | 설명 |
```
→ 태스크 description에 대상 파일 목록 포함

## 생성 로직

1. 플랜 문서를 읽고 구조 분석
2. 각 섹션/항목을 태스크로 변환:
   - **subject**: `[Phase X-N] 항목 제목` (70자 이내)
   - **description**: 변경 설명 + 대상 파일 목록 + 주의사항
   - **activeForm**: 진행형 한국어 (예: "역분개 모달 구현 중")
3. 실행 그래프 기반으로 `addBlockedBy` 설정
4. 병렬 표시(`‖`)된 태스크는 서로 의존성 없이 생성
5. 최종 검증 태스크 자동 추가 (`/verify` 실행)

## 출력

생성된 태스크 목록을 테이블로 출력:
```
| ID | Phase | Subject | Blocked By |
|----|-------|---------|------------|
| 1  | 0     | [Phase 0-1] 누계합계 수정 | — |
| 2  | 0     | [Phase 0-2] 역분개 날짜  | — |
| 5  | A     | [Phase A-1] date_field  | 1,2,3,4 |
```

사용자에게 확인 후 실행 시작 여부를 물음.
