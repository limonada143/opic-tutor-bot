"""/ start, /help, /stats 핸들러"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.database import upsert_user, get_user_stats
from handlers.auth import restricted


@restricted
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await upsert_user(user.id, user.username or "", user.first_name or "")

    keyboard = [
        [
            InlineKeyboardButton("📚 카테고리 연습", callback_data="mode:practice"),
            InlineKeyboardButton("📝 모의고사", callback_data="mode:mock"),
        ],
        [InlineKeyboardButton("📊 내 통계", callback_data="stats")],
    ]
    await update.message.reply_text(
        f"안녕하세요, {user.first_name}님! 👋\n\n"
        "🎯 *OPIc AI 튜터*에 오신 것을 환영합니다.\n\n"
        "• 영어로 답변하면 AI가 채점 + 피드백을 드립니다\n"
        "• 텍스트 또는 🎙 음성 메시지 모두 가능\n"
        "• 지난 실수를 기억해 개선 여부를 추적합니다\n\n"
        "무엇부터 시작할까요?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


@restricted
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "📖 *사용법*\n\n"
        "/start — 메인 메뉴\n"
        "/practice — 카테고리 선택 후 연습\n"
        "/mock — 모의고사 모드 (15문항)\n"
        "/skip — 현재 문제 건너뛰기\n"
        "/stop — 현재 세션 종료\n"
        "/stats — 내 학습 통계\n\n"
        "💡 *답변 방법*\n"
        "• 문제가 나오면 텍스트로 입력하거나\n"
        "• 🎙 음성 메시지를 보내세요\n\n"
        "채점 기준: AL > IH > IM3 > IM2 > IM1 > IL > NH"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@restricted
async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    stats = await get_user_stats(user.id)
    if not stats:
        await update.message.reply_text("아직 학습 기록이 없습니다. /start 로 시작해보세요!")
        return

    last = stats.get("last_attempt", "없음")
    if last and last != "없음":
        last = last[:10]  # 날짜만

    text = (
        f"📊 *{user.first_name}님의 학습 통계*\n\n"
        f"• 총 답변 횟수: {stats.get('total_attempts', 0)}회\n"
        f"• 총 세션 수: {stats.get('total_sessions', 0)}회\n"
        f"• 마지막 학습: {last}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
