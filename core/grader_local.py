"""Ollama 로컬 모델 기반 OPIc 채점 및 피드백 생성"""
import json
import aiohttp

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
MODEL = "qwen3.5:9b"

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

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(OLLAMA_URL, headers={"Content-Type": "application/json"}, json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise Exception(f"Ollama error {resp.status}: {data}")

    text = data["choices"][0]["message"]["content"].strip()

    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            start = part.find("{")
            end = part.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(part[start:end])
                except json.JSONDecodeError:
                    continue

    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError as e:
            raise Exception(f"JSON 파싱 실패. 오류: {e}\n모델 응답:\n{text[:500]}")

    raise Exception(f"JSON 파싱 실패. 모델 응답:\n{text[:500]}")
