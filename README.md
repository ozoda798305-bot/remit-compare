# 송금 최저가 에이전트 (한국 → 우즈베키스탄)

한국에서 일하는 우즈베키스탄 근로자가 월급을 가족의 UZCARD·HUMO 카드로 보낼 때, 업체마다 다른 환율과 수수료를 매일 자동으로 모아 **"총 100만 원을 내면 가족이 몇 솜을 받는가"** 하나의 기준으로 비교한다. 결과는 비교 보고서(HTML·PDF)와 우즈벡어·한국어 메시지로 나온다.

## 1. 설치 (처음 한 번)

Python 3.10 이상이 필요하다.

```bash
cd remit-compare
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

Google Chrome이 설치돼 있으면 마지막 줄은 생략해도 된다(설치된 크롬을 먼저 쓴다).

AI 단계(혜택 읽기, 수집 실패 복구)는 Gemini 무료 키가 필요하다. https://aistudio.google.com/apikey 에서 키를 만들고 `.env.example`을 `.env`로 복사해 `GEMINI_API_KEY=` 뒤에 넣는다. 키가 없으면 AI 단계만 「SKIP」으로 건너뛰고 나머지(견적 수집·비교·보고서)는 그대로 돈다.

## 2. 실행

```bash
python3 run.py
```

1~2분 안에 `output/<실행시각>/` 폴더에 결과가 생긴다.

| 파일 | 내용 |
|---|---|
| `report.pdf`, `report.html` | 비교 보고서(순위, 숨은 비용, 지금 쓰는 업체 대비 절약액, 추이, 검사 결과, 출처) |
| `message_uz.txt`, `message_ko.txt` | 메신저로 보내는 짧은 요약 |
| `quotes.json` | 수집한 원본 견적과 계산값 전체 |
| `run_log.json` | 단계별 성공·실패 기록 |

`data/history.csv`에 실행마다 견적이 쌓이고, 다음 실행에서 지난 실행과 비교해 1위 변경·급변을 알린다.

### 입력 예시

```bash
python3 run.py --amount 1500000 --my-provider e9pay     # 150만 원, 지금 E9pay를 쓰는 사람
python3 run.py --amount 500000 --my-provider gme
python3 run.py --providers hanpass,e9pay,hana --no-pdf  # 브라우저 없이 빠르게(10초 이내, AI 단계 없음)
python3 run.py --simulate-break gmoney                  # G-Money 수집기가 고장 났다고 가정하고 AI 복구를 시험
python3 run.py --refresh-promos                         # 저장된 혜택을 무시하고 공지를 새로 읽음
```

혜택 읽기는 6곳을 읽는 데 약 2분 걸려서 24시간에 한 번만 새로 읽고, 그 사이에는 `data/promotions.json`에 저장된 결과를 쓴다.

기본값은 `config.json`에서 바꾼다(`amount_krw`, `my_provider`, `sends_per_month`, 검사 기준, 하나은행 추정용 수수료).

## 3. 매일 자동 실행·웹 페이지·텔레그램

### GitHub Actions (기본)

`.github/workflows/daily.yml`이 매일 오전 9시(한국 시간)에 에이전트를 돌리고, 결과를 GitHub Pages 웹 페이지(https://ozoda798305-bot.github.io/remit-compare/)로 올리고, 실행 기록(`data/history.csv`)을 저장소에 저장한다. Actions 탭에서 「Run workflow」로 손으로도 돌릴 수 있다.

저장소 Settings → Secrets and variables → Actions 에 넣는 값:

| 이름 | 필요 여부 | 내용 |
|---|---|---|
| `GEMINI_API_KEY` | AI 단계용 | Gemini 무료 키 |
| `TELEGRAM_BOT_TOKEN` | 선택 | @BotFather 에서 `/newbot` 으로 받은 토큰 |
| `TELEGRAM_CHAT_ID` | 선택 | 봇에게 아무 메시지나 보낸 뒤 `python3 run.py --telegram-chat-id` 로 확인 |

텔레그램에는 요약 카드 이미지(우즈벡어) + 웹 링크, 이어서 한국어 요약이 온다.

### 내 컴퓨터에서 웹 폴더 만들기

```bash
python3 run.py --site _site     # _site/index.html, card.png, report.pdf, quotes.json, history.csv
```

### macOS·리눅스 cron (컴퓨터에서 돌릴 때)

매일 오전 9시:

```bash
crontab -e
# 아래 한 줄 추가 (경로는 자기 폴더로)
0 9 * * * cd /path/to/remit-compare && /usr/bin/env python3 run.py >> data/cron.log 2>&1
```

`.env.example`을 `.env`로 복사하고 텔레그램 봇 토큰·채팅 ID를 넣으면 결과 메시지가 텔레그램으로 온다. 비워 두면 보내기 단계만 건너뛴다.

## 4. 단계와 도구

| 단계 | 하는 일 | 도구·파일 | 실패로 보는 기준 |
|---|---|---|---|
| 1 입력 | 금액, 지금 쓰는 업체, 비교할 업체 | `config.json`, 명령줄 | — |
| 2 시장 환율 | 숨은 비용을 잴 기준 환율 | `agent/midrate.py` (open.er-api.com → currency-api → 우즈베키스탄 중앙은행 순서로 대체) | 세 출처 모두 실패 |
| 3 견적 수집 | 업체별 받는 금액·수수료 | `agent/providers/*.py` | 업체별 예외 → AI 복구 시도 → 그래도 실패하면 그 업체만 빼고 계속, 보고서에 표시 |
| 3-1 **AI 복구** | 수집기가 실패한 업체의 공개 페이지 화면 글자 전체를 Gemini에게 주고 견적을 뽑음 | `agent/ai_recover.py` | AI가 낸 금액이 화면 글자에 없으면 거부, 우즈베키스탄 견적이 화면에 없으면 「없음」 처리 |
| 4 **AI 혜택 읽기** | 업체 공지·이벤트·텔레그램 채널 6곳을 읽고 수수료 무료·우대 환율·쿠폰을 뽑음 | `agent/promotions.py` | 근거 문장이 원문에 그대로 없으면 버림(AI가 지어낸 것 차단), 끝난 혜택·다른 나라 전용 혜택 버림 |
| 5 검사·비교 | 총 지불액 기준으로 맞춤, 순위, 절약액, 혜택 반영 금액 | `agent/compare.py` | 시장 환율보다 0.5% 넘게 높음 / 10% 넘게 낮음 / 지난 실행 대비 ±5% 넘게 변동 |
| 6 기록 | 실행 기록 저장, 1위 변경 감지 | `agent/history.py`, `data/history.csv` | — |
| 7 보고서 | HTML·PDF·메시지 | `agent/report.py` | 견적 0건이면 만들지 않음 |
| 8 알림 | 텔레그램 전송(선택) | `agent/notify.py` | 전송 실패 코드 기록 |

순위는 카드로 바로 입금되는 송금 앱끼리만 매긴다. 은행(하나은행 SWIFT)은 송금 방식이 달라 순위에서 빼고 「참고」 줄로만 보여 준다.

### AI 단계 시험 기록 (2026-10-30)

| 시험 | 결과 |
|---|---|
| 혜택 읽기 6곳 | 한패스 「Send Now, Fly Free」(~10/31) 1건 채택, E9pay 추석 이벤트 2건은 「이미 끝난 혜택」으로 버림 |
| `--simulate-break gmoney` | 기존 수집기 실패 → AI가 공개 페이지에서 1,000,000원 → 8,905,644솜을 찾음, 화면 숫자 대조·시장 환율 검사 통과 |
| GME·한패스·E9pay AI 복구 | 첫 화면 계산기가 다른 나라 기준이라 AI가 「우즈베키스탄 견적 없음」으로 답함(숫자를 지어내지 않음) |

## 5. 업체별 수집 방식

| 업체 | 방식 | 근거 |
|---|---|---|
| 한패스 | 홈페이지 환율 계산기가 부르는 견적 주소(app.hanpass.com) 조회 | 이 주소에는 robots.txt 제한이 없다 |
| E9pay | 홈페이지 환전 시뮬레이션 주소 조회, 수수료는 홈페이지의 송금방법 목록에서 읽음 | robots.txt 없음 |
| GME | 공개 홈페이지를 브라우저(Playwright)로 열어 우즈베키스탄·UZS를 고르고 화면 숫자를 읽음 | 계산기 내부 주소(/api/)는 robots.txt 금지라 직접 부르지 않는다 |
| G-Money | 공개 페이지 '한국→우즈베키스탄 송금'을 브라우저로 열어 계산기 숫자를 읽음 | 계산기 서버(mapi.gmoneytrans.net)는 robots.txt 전체 금지라 직접 부르지 않는다 |
| 하나은행 | 실시간 견적이 앱 안에만 있어 약관 공식으로 추정(입금액 − 송금수수료 − 전신료, 전신환매도율 적용, 중개은행 수수료) | 하나은행 해외송금 약관 제7·8조. 수수료 값은 `config.json`의 가정값 |

모든 수집은 실행 1회에 업체당 1~2번만 조회한다.

## 6. 알려진 한계

- 하나은행은 추정치라 보고서에 「추정」으로 표시한다.
- 업체 홈페이지 구조가 바뀌면 해당 수집기가 실패한다. 실패한 업체는 보고서 맨 위에 표시되고 나머지로 계속 진행한다.
- 시장 환율 출처(open.er-api.com)는 하루 한 번 갱신되므로 숨은 비용 %는 근삿값이다.
