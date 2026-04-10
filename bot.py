"""OPIc AI Tutor Bot - 메인 진입점"""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from config import TELEGRAM_BOT_TOKEN
from db.database import init_db
from core.questions import load_questions
from handlers.start import cmd_start, cmd_help, cmd_stats
from handlers.quiz import (
    cmd_practice,
    cmd_mock,
    cmd_skip,
    cmd_stop,
    handle_text_answer,
    handle_voice_answer,
    handle_callback,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    await init_db()
    load_questions()
    logger.info("DB 초기화 및 문제 뱅크 로드 완료")


def main() -> None:
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # 커맨드 핸들러
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("practice", cmd_practice))
    app.add_handler(CommandHandler("mock", cmd_mock))
    app.add_handler(CommandHandler("skip", cmd_skip))
    app.add_handler(CommandHandler("stop", cmd_stop))

    # 메시지 핸들러
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_answer))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_answer))

    # 콜백 버튼 핸들러
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("OPIc AI Tutor Bot 시작")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
