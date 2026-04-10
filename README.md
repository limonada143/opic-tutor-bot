# OPIc AI Tutor Bot

텔레그램 기반 OPIc 영어 말하기 시험 AI 튜터봇.
텍스트 또는 음성으로 답변하면 Claude가 ACTFL 기준으로 채점 + 피드백을 제공합니다.

## 기능

- **카테고리 연습**: 자기소개, 일상생활, 취미, 여행, 돌발 주제, 롤플레이
- **모의고사 모드**: 실제 시험 비중과 유사한 15문항 자동 큐레이션
- **음성 답변**: 텔레그램 음성 메시지 → Whisper STT → AI 채점
- **AI 채점**: Claude 기반 AL/IH/IM/IL/NH 레벨 채점 + 구체적 피드백
- **실수 추적**: 이전 오류를 기억해 개선 여부 추적
- **멀티유저**: 화이트리스트 기반 초대 유저만 접근 가능

## 설치

```bash
git clone <repo-url>
cd opic-tutor-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env 파일에 토큰/키 입력
```

## 환경변수 (.env)

| 변수 | 설명 |
|------|------|
| `TELEGRAM_BOT_TOKEN` | BotFather에서 발급 |
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `OPENAI_API_KEY` | Whisper STT용 (음성 기능 사용 시) |
| `ALLOWED_USER_IDS` | 허용할 Telegram User ID (쉼표 구분) |
| `ADMIN_USER_ID` | 관리자 ID |

## 실행

```bash
python bot.py
```

## 문제 뱅크 추가

[data/questions.json](data/questions.json)의 각 카테고리 `questions` 배열에 추가:

```json
{
  "id": "unique_id",
  "text": "Tell me about...",
  "difficulty": "IM",
  "tips": "답변 팁 (선택)"
}
```

## 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/start` | 메인 메뉴 |
| `/practice` | 카테고리 선택 후 연습 |
| `/mock` | 모의고사 모드 (15문항) |
| `/skip` | 현재 문제 건너뛰기 |
| `/stop` | 세션 종료 |
| `/stats` | 내 학습 통계 |
| `/help` | 도움말 |

## 프로젝트 구조

```
opic-tutor-bot/
├── bot.py              # 메인 진입점
├── config.py           # 환경변수 설정
├── handlers/
│   ├── auth.py         # 접근 제어
│   ├── start.py        # /start, /help, /stats
│   └── quiz.py         # 문제 출제 + 답변 처리
├── core/
│   ├── questions.py    # 문제 뱅크 로딩/추출
│   ├── grader.py       # Claude 채점 + 피드백
│   ├── stt.py          # Whisper STT
│   └── session.py      # 인메모리 유저 상태
├── db/
│   └── database.py     # SQLite (유저, 세션, 학습 기록)
└── data/
    └── questions.json  # 문제 뱅크
```
