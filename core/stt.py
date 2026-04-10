"""OpenAI Whisper를 이용한 음성 → 텍스트 변환"""
import aiofiles
import openai
from config import OPENAI_API_KEY

_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)


async def transcribe(audio_path: str) -> str:
    """오디오 파일을 텍스트로 변환합니다. (한국어/영어 혼용 지원)"""
    async with aiofiles.open(audio_path, "rb") as f:
        audio_bytes = await f.read()

    # Whisper는 동기 API이므로 bytes를 직접 전달
    import io
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "voice.ogg"  # Telegram 음성 메시지 형식

    transcript = await _client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="en",          # OPIc은 영어 답변
        prompt="This is an OPIc English speaking test response.",
    )
    return transcript.text.strip()
