# 로컬 세션 시작 가이드

클라우드 세션에서 준비한 작업을 로컬 Claude Code 세션으로 이어받기 위한 문서.
**인수인계로 따로 복붙할 자료는 없습니다.** 이 브랜치를 clone 하고, 아래 프롬프트만 붙여넣으면 됩니다.

---

## 0단계 — 준비물 확인

터미널을 열고 아래 세 줄을 **한 줄씩** 입력해 보세요. 버전 번호가 나오면 설치된 것입니다.

```
git --version
python3 --version
claude --version
```

- 터미널 여는 법 — **Mac**: `Command + Space` → "터미널" 검색 / **Windows**: 시작 버튼 → "PowerShell" 검색
- Windows에서는 `python3` 대신 `python` 으로 확인하세요.
- `claude` 가 없다고 나오면: Node.js 설치 후 `npm install -g @anthropic-ai/claude-code`
- `git` 이 없다고 나오면: Mac은 `xcode-select --install`, Windows는 https://git-scm.com 에서 설치

---

## 1단계 — 내려받기 (한 줄씩)

```
git clone https://github.com/dreamerstar88-ui/market-dashboard.git
```
```
cd market-dashboard
```
```
git checkout claude/banpo-lamian-transaction-data-rjc2kf
```

내려받은 폴더는 터미널을 열었을 때의 현재 위치(보통 사용자 홈 폴더)에 생깁니다.

---

## 2단계 — 인증키 파일 만들기

`market-dashboard` 폴더 안에서, `인증키` 자리에 **실제 발급받은 키를 넣어** 한 줄 입력하세요.

**Mac / Linux**
```
echo '인증키' > .molit_key
```

**Windows PowerShell**
```
'인증키' | Out-File -Encoding ascii .molit_key
```

- 이 파일은 `.gitignore` 에 등록되어 있어 **GitHub에 올라가지 않습니다.**
- 환경변수(`export MOLIT_SERVICE_KEY=...`)를 설정해도 되지만, 파일 방식이 더 간단하고 터미널을 새로 열어도 유지됩니다.
- 제대로 만들어졌는지 확인: Mac/Linux `cat .molit_key`, Windows `type .molit_key`

---

## 3단계 — Claude 실행

```
claude
```

## 4단계 — 새 세션 첫 메시지 (아래 블록 그대로 복사)

```
이 저장소의 docs/banpo_raemian/HANDOFF.md 를 먼저 읽어줘.
클라우드 세션에서 작업하다가 네트워크 차단으로 수집만 못 하고 넘어온 건이라,
그 문서에 배경·제약·실행법이 다 정리돼 있어.

목표: 서울 서초구 반포동 래미안퍼스티지(18-1, 2009년 7월 입주)의
국토부 실거래가를 전량 수집해서 매매 / 전세 / 월세 × 평형별 두 축으로 정리하는 것.

공공데이터포털 인증키는 저장소 루트의 .molit_key 파일에 넣어뒀어.

순서대로 진행해줘:
1. 오프라인 테스트 두 개를 돌려서 환경부터 확인
   (scripts/test_molit_rtms_offline.py, scripts/test_firstige_offline.py)
2. 1개월치만 짧게 실제 API를 호출해서 인증키가 먹는지,
   응답에 rgstDate(등기일자)가 오는지 확인
3. 되면 python scripts/firstige_report.py --start 200901 --outdir data/firstige 실행
4. 끝나면 data/firstige/REPORT_firstige.md 를 읽고 결과를 요약해줘.
   특히 누락된 월은 없는지, 연도별 건수가 비정상적으로 끊기는 구간은 없는지,
   2023년 이후 등기일자 보유 비율이 정상인지 점검해줘.
```

---

## 5단계 — 결과 확인 포인트

수집이 끝나면 아래를 함께 점검해달라고 하세요.

| 확인 항목 | 정상 기준 |
|---|---|
| 누락 월 | 스크립트가 월별 `totalCount`와 수집 건수를 대조. 불일치 시 경고 + 종료코드 1 |
| 2009년 이전이 비어 있음 | **정상.** 퍼스티지는 2009-07 입주로, 그 이전은 "반포주공2단지"로 신고됨 |
| 2022년 이전 등기일자가 공란 | **정상.** 국토부가 2023-01-01 계약분부터만 공개 |
| 해제(취소) 거래 | 집계에서 제외되고 건수만 따로 표기되어야 함 |
| 전세/월세 분리 | 월세금액 0 → 전세, 0 초과 → 월세 |

---

## 6단계 — 막힐 때

| 증상 | 대응 |
|---|---|
| `SERVICE_KEY_IS_NOT_REGISTERED_ERROR` | 활용신청 승인 전이거나 Encoding 키를 넣은 경우. **Decoding 키**를 쓰고 1~2시간 대기 |
| `LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR` | 일일 호출 한도 초과. 캐시가 남아 있으니 다음 날 같은 명령으로 이어서 실행 |
| 중간에 끊김 | 같은 명령 재실행. `data/firstige/_cache/` 에 받은 월은 재호출하지 않음 |
| 응답은 오는데 0건 | 단지명 표기 확인. 필터는 공백 제거 후 `래미안퍼스티지` 부분일치 |
| 인증키를 못 찾는다는 오류 | 오류 메시지에 `.molit_key` 를 만들 절대경로가 찍힙니다. 그 위치에 만드세요 |

---

## 참고 — 범위 확대

퍼스티지 외 반포·잠원 래미안 7개 단지 전체가 필요해지면:

```bash
python scripts/collect_banpo_raemian.py --start 200601 --outdir data/banpo_raemian
```

트리니원(2026-08 입주)은 아직 거래가 입주권으로 잡히므로 `--kinds` 에 `분양권` 포함 필수
(기본값 `매매,분양권,전월세` 에 이미 포함).

---

## 정리 — 넘길 자료 목록

| 넘길 것 | 방법 |
|---|---|
| 코드·문서 전부 | 브랜치 `claude/banpo-lamian-transaction-data-rjc2kf` clone |
| 배경·제약·이력 | `docs/banpo_raemian/HANDOFF.md` (새 세션이 직접 읽음) |
| 첫 메시지 | 위 2단계 블록 복붙 |
| 인증키 | 저장소 루트 `.molit_key` 파일 (gitignore 처리, 대화에 붙여넣지 않음) |

이전 대화 내용을 옮길 필요는 없습니다.
