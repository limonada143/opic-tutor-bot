"""오답 기반 복습 문제 생성 로직"""
import aiohttp
from config import OPENROUTER_API_KEY

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemma-3-12b-it:free"


def format_review_message(mistakes: list[dict]) -> str:
    """오답 노트 메시지 포맷"""
    if not mistakes:
        return "아직 기록된 오답이 없습니다. /practice 또는 /mock 으로 먼저 답변해보세요!"

    lines = ["📓 *오답 노트 (최근 실수)*\n"]
    for i, m in enumerate(mistakes, 1):
        etype = m.get("error_type", "기타")
        example = m.get("example", "")
        corrected = m.get("corrected", "")
        lines.append(f"*{i}. [{etype}]*")
        lines.append(f"  ❌ `{example}`")
        lines.append(f"  ✅ `{corrected}`")
        lines.append("")
    return "\n".join(lines)


async def generate_review_question(mistakes: list[dict]) -> str:
    """실수 패턴을 바탕으로 타깃 복습 문제 생성"""
    if not mistakes:
        return "Tell me about a typical day in your life."

    mistake_summary = "\n".join(
        f"- [{m['error_type']}] {m['example']} → {m['corrected']}"
        for m in mistakes
    )

    prompt = (
        "Based on the following English mistakes made by an OPIc learner, "
        "generate ONE short OPIc-style speaking question in English that naturally "
        "encourages practice of the corrected expressions. "
        "Return only the question text, nothing else.\n\n"
        f"Mistakes:\n{mistake_summary}"
    )

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENROUTER_URL, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    return "Tell me about a recent experience that was memorable for you."
                data = await resp.json()
        return data["choices"][0]["message"]["content"].strip().strip('"')
    except Exception:
        return "Tell me about a recent experience that was memorable for you."
