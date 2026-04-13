# /session-save — 세션 상태 저장

현재 작업 상태를 `.claude/sessions/` 디렉토리에 저장하여, 새로운 대화에서 즉시 이어갈 수 있게 합니다.

## 저장 내용

### STATE.md (자동 생성)
```markdown
# Session State
- **저장 시각**: 2026-03-24T04:30:00+09:00
- **브랜치**: main
- **최근 커밋**: abc1234 — 커밋 메시지
- **CI 상태**: green / red (마지막 run 결과)

## 진행 중인 작업
- [완료] Phase 0 핫픽스 4건
- [완료] Phase A 병렬 4건
- [진행중] Phase B frontend...
- [대기] Phase C 검증

## 미해결 이슈
- issue 설명...

## 다음 할 일
1. 첫 번째
2. 두 번째

## 변경된 파일 (uncommitted)
- path/to/file.py (modified)

## 관련 플랜
- .claude/plans/plan-name.md
```

## 실행 로직

1. `git status`, `git log -1`, `gh run list --limit 1`로 현재 상태 수집
2. TaskList로 진행 중/대기 태스크 수집
3. 현재 대화 맥락에서 핵심 정보 추출:
   - 무엇을 하고 있었는지
   - 어디서 막혔는지 (있다면)
   - 다음에 해야 할 것
4. `.claude/sessions/STATE.md`에 저장 (이전 상태 덮어쓰기)
5. 사용자에게 저장 완료 확인

## 복원

새 세션에서 사용자가 "이어서 하자" 또는 "지난번 작업 이어가기" 등을 말하면:
1. `.claude/sessions/STATE.md` 읽기
2. 상태 요약 출력
3. 다음 할 일 제안
