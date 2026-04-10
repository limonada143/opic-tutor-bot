"""Claude 기반 OPIc 채점 및 피드백 생성"""
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert OPIc (Oral Proficiency Interview by Computer) tutor and evaluator.
You assess responses based on ACTFL guidelines and provide constructive feedback in Korean.

Scoring levels: AL (Advanced Low) > IH (Intermediate High) > IM3 > IM2 > IM1 > IL (Intermediate Low) > NH (Novice High)

Always respond in this exact JSON format:
{
  "score": "<level>",
  "score_reason": "<why this score in Korean, 1-2 sentences>",
  "strengths": ["<strength 1 in Korean>", "<strength 2>"],
  "improvements": [
    {
      "issue": "<문제점 Korean>",
      "original": "<user's exact words>",
      "corrected": "<better version>",
      "explanation": "<why it's better, Korean>"
    }
  ],
  "model_answer_snippet": "<1-2 sentences showing a higher-level version of their answer>",
  "error_types": ["tense", "vocabulary", "fluency", "grammar"]
}"""


async def grade_answer(question: str, answer: str, recent_mistakes: list[dict]) -> dict:
    """답변을 채점하고 피드백을 반환합니다."""
    mistake_context = ""
    if recent_mistakes:
        items = "\n".join(
            f"- [{m['error_type']}] {m['example']} → {m['corrected']}"
            for m in recent_mistakes
        )
        mistake_context = f"\n\n[이전 실수 패턴 (개선 여부 확인)]\n{items}"

    user_prompt = f"""Question: {question}

User's Answer: {answer}{mistake_context}

Please evaluate this OPIc response."""

    message = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}]
    )

    import json
    text = message.content[0].text.strip()
    # JSON 블록 파싱
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def format_feedback(feedback: dict, answer_type: str = "text") -> str:
    """피드백 dict → 텔레그램 메시지 포맷"""
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
        for imp in improvements:
            lines.append(f"  • *{imp['issue']}*")
            if imp.get("original"):
                lines.append(f"    ❌ `{imp['original']}`")
                lines.append(f"    ✅ `{imp['corrected']}`")
                lines.append(f"    _{imp['explanation']}_")
        lines.append("")

    if model_snippet:
        lines.append("💡 *한 단계 높은 표현*")
        lines.append(f"_{model_snippet}_")

    return "\n".join(lines)
