"""오답 노트 조회 및 복습 모드 핸들러"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.reviewer_router import format_review_message, generate_review_question
from core.session import get_state, Mode
from db.database import get_recent_mistakes, start_session
from handlers.auth import restricted


@restricted
async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """오답 노트 조회"""
    user = update.effective_user
    mistakes = await get_recent_mistakes(user.id, limit=5)

    text = format_review_message(mistakes)

    if mistakes:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 재도전 문제 받기", callback_data="review:challenge")]
        ])
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="Markdown")


async def handle_review_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """재도전 맞춤 문제 생성 콜백"""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    await query.message.reply_text("⏳ 맞춤 복습 문제를 생성 중입니다...")

    mistakes = await get_recent_mistakes(user.id, limit=5)
    question_text = await generate_review_question(mistakes)

    state = get_state(user.id)
    state.mode = Mode.PRACTICE
    state.current_category = "review"
    state.session_id = await start_session(user.id, "practice")
    state.current_question = {
        "id": f"review_{user.id}",
        "text": question_text,
        "tips": "이전 실수를 교정한 표현을 활용해 답변해보세요.",
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ 건너뛰기", callback_data="skip"),
         InlineKeyboardButton("🛑 중단", callback_data="stop")]
    ])
    text = (
        f"🔁 *맞춤 복습 문제*\n\n"
        f"{question_text}\n\n"
        "_이전 실수를 교정한 표현을 활용해 답변해보세요._\n\n"
        "💬 텍스트 또는 🎙 음성 메시지로 답변하세요."
    )
    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
