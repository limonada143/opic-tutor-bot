"""OpenRouter 기반 OPIc 채점 및 피드백 생성"""
import json
import aiohttp
from config import OPENROUTER_API_KEY

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemma-3-12b-it:free"

SYSTEM_PROMPT = """You are an expert OPIc (Oral Proficiency Interview by Computer) tutor and evaluator.
You assess responses based on ACTFL guidelines and provide constructive feedback in Korean.

Scoring levels: AL (Advanced Low) > IH (Intermediate High) > IM3 > IM2 > IM1 > IL (Intermediate Low) > NH (Novice High)

IMPORTANT: In the "improvements" array, include EVERY sentence from the user's answer that has an error or room for improvement.
- For sentences with errors, show the problem clearly and provide a corrected version.
- Skip sentences that are perfectly natural and correct — only include ones that need work.

Always respond in this exact JSON format with no additional text:
{
  "score": "<level>",
  "score_reason": "<why this score in Korean, 1-2 sentences>",
  "strengths": ["<strength 1 in Korean>", "<strength 2>"],
  "improvements": [
    {
      "issue": "<문제점 or ✅ 잘 표현됨>",
      "original": "<user's exact sentence>",
      "corrected": "<corrected or elevated version>",
      "explanation": "<why it's better or what was good, Korean>"
    }
  ],
  "model_answer_snippet": "<2-3 sentences showing a higher-level version of their answer>",
  "error_types": ["tense", "vocabulary", "fluency", "grammar"]
}"""


async def grade_answer(question: str, answer: str, recent_mistakes: list, fluency: dict = None) -> dict:
    mistake_context = ""
    if recent_mistakes:
        items = "\n".join(
            f"- [{m['error_type']}] {m['example']} → {m['corrected']}"
            for m in recent_mistakes
        )
        mistake_context = f"\n\n[이전 실수 패턴 (개선 여부 확인)]\n{items}"

    fluency_context = ""
    if fluency:
        fluency_context = f"""

[음성 유창성 데이터]
- 발화 시간: {fluency['duration_sec']}초
- 단어 수: {fluency['word_count']}개
- 말하기 속도: {fluency['wpm']} WPM (원어민 평균: 130~150 WPM)
- 침묵 구간 (0.5초↑): {fluency['pause_count']}회
- 필러 워드: {fluency['filler_count']}회 {('(' + ', '.join(fluency['filler_words']) + ')') if fluency['filler_words'] else ''}

위 데이터를 바탕으로 fluency 항목을 채점에 반영하고, improvements에 구체적인 유창성 피드백을 포함하세요."""

    user_prompt = f"""Question: {question}

User's Answer: {answer}{mistake_context}{fluency_context}

Return only JSON, no other text."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(OPENROUTER_URL, headers=headers, json=payload) as resp:
            data = await resp.json()
            if resp.status != 200 or "choices" not in data:
                error_msg = data.get("error", {}).get("message", str(data))
                raise Exception(f"OpenRouter error {resp.status}: {error_msg}")

    text = data["choices"][0]["message"]["content"].strip()

    # ```json ... ``` 블록 추출
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except json.JSONDecodeError:
                continue

    # { } 사이 JSON 직접 추출
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(text[start:end])

    raise Exception(f"JSON 파싱 실패. 모델 응답:\n{text[:300]}")


def format_fluency_summary(fluency: dict) -> str:
    """유창성 수치 요약 메시지"""
    wpm = fluency["wpm"]
    if wpm < 80:
        pace = "느림 (자신감 있게 더 빠르게 말해보세요)"
    elif wpm > 160:
        pace = "빠름 (너무 빠르면 명료성이 떨어질 수 있어요)"
    else:
        pace = "적절함 ✅"

    lines = [
        "🎙 *음성 유창성 분석*",
        f"  • 말하기 속도: {fluency['wpm']} WPM — {pace}",
        f"  • 침묵 구간: {fluency['pause_count']}회",
    ]
    if fluency["filler_count"] > 0:
        lines.append(f"  • 필러 워드: {fluency['filler_count']}회 ({', '.join(fluency['filler_words'])})")
    else:
        lines.append("  • 필러 워드: 없음 ✅")

    return "\n".join(lines)


def format_feedback(feedback: dict, answer_type: str = "text") -> str:
    score = feedback.get("score", "?")
    reason = feedback.get("score_reason", "")
    strengths = feedback.get("strengths", [])
    improvements = feedback.get("improvements", [])
    model_snippet = feedback.get("model_answer_snippet", "")

    lines = [
        f"📊 *채점 결과: {score}*",
        f"_{reason}_",
        "",
    ]

    if answer_type == "voice":
        lines.insert(1, "🎙 _음성 답변이 텍스트로 변환되었습니다._\n")

    if strengths:
        lines.append("✅ *잘한 점*")
        for s in strengths:
            lines.append(f"  • {s}")
        lines.append("")

    if improvements:
        lines.append("🔧 *개선할 점*")
        for i, imp in enumerate(improvements, 1):
            issue = imp.get("issue", "")
            lines.append(f"\n*[{i}]* {issue}")
            if imp.get("original"):
                lines.append(f"  ❌ `{imp['original']}`")
                lines.append(f"  ✅ `{imp['corrected']}`")
                lines.append(f"  _{imp['explanation']}_")
        lines.append("")

    if model_snippet:
        lines.append("💡 *한 단계 높은 표현*")
        lines.append(f"_{model_snippet}_")

    return "\n".join(lines)
