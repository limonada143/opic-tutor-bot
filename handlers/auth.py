"""접근 제어 미들웨어"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config import ALLOWED_USER_IDS


def restricted(func):
    """허용된 유저만 명령어 실행 가능"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user.id not in ALLOWED_USER_IDS:
            await update.message.reply_text(
                "⛔ 이 봇은 초대된 사용자만 이용할 수 있습니다.\n"
                "관리자에게 문의하세요."
            )
            return
        return await func(update, context)
    return wrapper
