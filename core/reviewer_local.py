"""Ollama 로컬 모델 기반 복습 문제 생성"""
import aiohttp
from core.reviewer import format_review_message

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL = "qwen3.5:9b"


async def generate_review_question(mistakes: list[dict]) -> str:
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

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
            ) as resp:
                if resp.status != 200:
                    return "Tell me about a recent experience that was memorable for you."
                data = await resp.json()
        return data["choices"][0]["message"]["content"].strip().strip('"')
    except Exception:
        return "Tell me about a recent experience that was memorable for you."
