"""GRADER_MODE 환경변수에 따라 local/remote 채점기 선택"""
from config import GRADER_MODE

if GRADER_MODE == "local":
    from core.grader_local import grade_answer
else:
    from core.grader import grade_answer

from core.grader import format_feedback, format_fluency_summary
