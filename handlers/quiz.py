"""문제 출제, 답변 처리, 채점 핸들러"""
import os
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.questions import get_categories, get_random_question, get_mock_exam_questions
from core.session import get_state, Mode
from core.grader_router import grade_answer, format_feedback, format_fluency_summary
from core.stt import transcribe
from db.database import start_session, end_session, save_attempt, get_recent_mistakes, save_mistake
from handlers.auth import restricted


def _category_keyboard() -> InlineKeyboardMarkup:
    cats = get_categories()
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"cat:{cid}")]
        for cid, label in cats.items()
    ]
    buttons.append([InlineKeyboardButton("❌ 취소", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


async def _send_question(update: Update, question: dict, index: int = 0, total: int = 0) -> None:
    header = f"*[{index}/{total}]* " if total > 0 else ""
    text = (
        f"🎯 {header}*질문*\n\n"
        f"{question['text']}\n\n"
        "💬 텍스트 또는 🎙 음성 메시지로 답변하세요."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ 건너뛰기", callback_data="skip"),
         InlineKeyboardButton("🛑 중단", callback_data="stop")]
    ])
    msg = update.message or update.callback_query.message
    await msg.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


@restricted
async def cmd_practice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📚 *카테고리를 선택하세요*",
        parse_mode="Markdown",
        reply_markup=_category_keyboard(),
    )


@restricted
async def cmd_mock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    state = get_state(user.id)

    questions = get_mock_exam_questions()
    if not questions:
        await update.message.reply_text("⚠️ 문제 뱅크가 비어 있습니다. 관리자에게 문의하세요.")
        return

    state.mode = Mode.MOCK
    state.mock_questions = questions
    state.mock_index = 0
    state.session_id = await start_session(user.id, "mock")

    await update.message.reply_text(
        f"📝 *모의고사 시작!*\n\n총 {len(questions)}문항입니다.\n"
        "실제 시험처럼 편하게 답변해보세요.",
        parse_mode="Markdown",
    )
    state.current_question = questions[0]
    await _send_question(update, questions[0], index=1, total=len(questions))


@restricted
async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    state = get_state(user.id)
    if state.mode == Mode.IDLE or not state.current_question:
        await update.message.reply_text("현재 진행 중인 문제가 없습니다.")
        return
    await _next_question(update, user.id, state)


@restricted
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    state = get_state(user.id)
    if state.session_id:
        await end_session(state.session_id)
    state.reset()
    await update.message.reply_text(
        "세션을 종료했습니다. 수고하셨습니다! 💪\n/start 로 다시 시작할 수 있습니다."
    )


async def _next_question(update, user_id: int, state) -> None:
    """모의고사: 다음 문제로 이동 / 연습: 같은 카테고리에서 새 문제"""
    if state.mode == Mode.MOCK:
        state.mock_index += 1
        if state.mock_index >= len(state.mock_questions):
            # 모의고사 종료
            if state.session_id:
                await end_session(state.session_id)
            state.reset()
            msg = update.message or update.callback_query.message
            await msg.reply_text(
                "🎉 *모의고사 완료!*\n\n수고하셨습니다. /stats 로 학습 통계를 확인해보세요.",
                parse_mode="Markdown",
            )
            return
        q = state.mock_questions[state.mock_index]
        state.current_question = q
        await _send_question(
            update, q,
            index=state.mock_index + 1,
            total=len(state.mock_questions)
        )
    else:  # PRACTICE
        q = get_random_question(state.current_category)
        if not q:
            state.reset()
            msg = update.message or update.callback_query.message
            await msg.reply_text("해당 카테고리에 더 이상 문제가 없습니다. /practice 로 다시 선택하세요.")
            return
        state.current_question = q
        await _send_question(update, q)


async def _after_answer(update, user_id: int, state) -> None:
    """답변 후 처리: 모의고사는 자동으로 다음 문제, 연습 모드는 버튼으로 선택"""
    msg = update.message or update.callback_query.message

    if state.mode == Mode.MOCK:
        await _next_question(update, user_id, state)
    else:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔁 다시 하기", callback_data="retry"),
                InlineKeyboardButton("➡️ 다음 문제", callback_data="next"),
            ],
            [InlineKeyboardButton("🛑 그만하기", callback_data="stop")],
        ])
        await msg.reply_text("다음 문제로 넘어갈까요?", reply_markup=keyboard)


async def handle_text_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """텍스트 답변 처리"""
    user = update.effective_user
    if user.id not in __import__("config").ALLOWED_USER_IDS:
        return

    state = get_state(user.id)
    if state.mode == Mode.IDLE or not state.current_question:
        return  # 문제 진행 중이 아니면 무시

    answer = update.message.text.strip()
    question = state.current_question

    await update.message.reply_text("⏳ 채점 중입니다...")

    try:
        recent_mistakes = await get_recent_mistakes(user.id)
        feedback = await grade_answer(question["text"], answer, recent_mistakes)
        feedback_text = format_feedback(feedback, "text")

        await update.message.reply_text(feedback_text, parse_mode="Markdown")

        for imp in feedback.get("improvements", []):
            if imp.get("original"):
                for etype in feedback.get("error_types", ["grammar"]):
                    await save_mistake(user.id, etype, imp["original"], imp["corrected"])
                    break

        await save_attempt(
            user_id=user.id,
            session_id=state.session_id,
            question_id=question["id"],
            question_text=question["text"],
            answer_type="text",
            answer_text=answer,
            score=feedback.get("score", "?"),
            feedback=feedback,
        )

        await _after_answer(update, user.id, state)

    except Exception as e:
        await update.message.reply_text(f"⚠️ 채점 중 오류가 발생했습니다: {e}")


async def handle_voice_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """음성 메시지 처리: STT → 채점"""
    user = update.effective_user
    if user.id not in __import__("config").ALLOWED_USER_IDS:
        return

    state = get_state(user.id)
    if state.mode == Mode.IDLE or not state.current_question:
        await update.message.reply_text("먼저 문제를 시작하세요. /practice 또는 /mock")
        return

    await update.message.reply_text("🎙 음성을 분석 중입니다...")

    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name

        await file.download_to_drive(tmp_path)
        stt_result = await transcribe(tmp_path)
        os.unlink(tmp_path)

        answer_text = stt_result["text"]
        fluency = stt_result["fluency"]

        if not answer_text:
            await update.message.reply_text("음성을 인식하지 못했습니다. 다시 시도해주세요.")
            return

        await update.message.reply_text(f"📝 *인식된 텍스트:*\n_{answer_text}_", parse_mode="Markdown")

        question = state.current_question
        recent_mistakes = await get_recent_mistakes(user.id)
        feedback = await grade_answer(question["text"], answer_text, recent_mistakes, fluency=fluency)

        await update.message.reply_text(format_fluency_summary(fluency), parse_mode="Markdown")
        await update.message.reply_text(format_feedback(feedback, "voice"), parse_mode="Markdown")

        for imp in feedback.get("improvements", []):
            if imp.get("original"):
                for etype in feedback.get("error_types", ["grammar"]):
                    await save_mistake(user.id, etype, imp["original"], imp["corrected"])
                    break

        await save_attempt(
            user_id=user.id,
            session_id=state.session_id,
            question_id=question["id"],
            question_text=question["text"],
            answer_type="voice",
            answer_text=answer_text,
            score=feedback.get("score", "?"),
            feedback=feedback,
            fluency=fluency,
        )

        await _after_answer(update, user.id, state)

    except Exception as e:
        await update.message.reply_text(f"⚠️ 음성 처리 중 오류: {e}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """인라인 버튼 콜백 처리"""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    if data.startswith("cat:"):
        category = data[4:]
        state = get_state(user.id)
        state.mode = Mode.PRACTICE
        state.current_category = category
        state.session_id = await start_session(user.id, "practice")

        q = get_random_question(category)
        if not q:
            await query.message.reply_text("⚠️ 해당 카테고리에 문제가 없습니다. 곧 추가될 예정입니다!")
            state.reset()
            return
        state.current_question = q
        cats = get_categories()
        await query.message.reply_text(f"📚 *{cats.get(category, category)} 연습 시작!*", parse_mode="Markdown")
        await _send_question(update, q)

    elif data == "mode:practice":
        await query.message.reply_text(
            "📚 *카테고리를 선택하세요*",
            parse_mode="Markdown",
            reply_markup=_category_keyboard(),
        )

    elif data == "mode:mock":
        # /mock 과 동일 로직
        questions = get_mock_exam_questions()
        if not questions:
            await query.message.reply_text("⚠️ 문제 뱅크가 비어 있습니다.")
            return
        state = get_state(user.id)
        state.mode = Mode.MOCK
        state.mock_questions = questions
        state.mock_index = 0
        state.session_id = await start_session(user.id, "mock")
        await query.message.reply_text(
            f"📝 *모의고사 시작!*\n총 {len(questions)}문항입니다.",
            parse_mode="Markdown",
        )
        state.current_question = questions[0]
        await _send_question(update, questions[0], index=1, total=len(questions))

    elif data == "stats":
        from db.database import get_user_stats
        stats = await get_user_stats(user.id)
        if not stats:
            await query.message.reply_text("아직 학습 기록이 없습니다.")
            return
        last = (stats.get("last_attempt") or "없음")[:10]
        text = (
            f"📊 *학습 통계*\n\n"
            f"• 총 답변: {stats.get('total_attempts', 0)}회\n"
            f"• 총 세션: {stats.get('total_sessions', 0)}회\n"
            f"• 마지막 학습: {last}"
        )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "retry":
        state = get_state(user.id)
        if state.mode != Mode.IDLE and state.current_question:
            await _send_question(update, state.current_question)

    elif data == "next":
        state = get_state(user.id)
        if state.mode != Mode.IDLE and state.current_question:
            await _next_question(update, user.id, state)

    elif data == "skip":
        state = get_state(user.id)
        if state.mode != Mode.IDLE and state.current_question:
            await _next_question(update, user.id, state)

    elif data in ("stop", "cancel"):
        state = get_state(user.id)
        if state.session_id:
            await end_session(state.session_id)
        state.reset()
        await query.message.reply_text("세션을 종료했습니다. /start 로 다시 시작하세요.")
