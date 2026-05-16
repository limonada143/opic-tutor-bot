"""GRADER_MODE 환경변수에 따라 local/remote 복습기 선택"""
from config import GRADER_MODE

if GRADER_MODE == "local":
    from core.reviewer_local import generate_review_question
else:
    from core.reviewer import generate_review_question

from core.reviewer import format_review_message
