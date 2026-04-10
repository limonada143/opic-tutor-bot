"""인메모리 유저 상태 관리 (현재 문제, 모드 등)"""
from dataclasses import dataclass, field
from enum import Enum


class Mode(str, Enum):
    IDLE = "idle"
    PRACTICE = "practice"   # 카테고리별 연습
    MOCK = "mock"           # 모의고사 (15문항)


@dataclass
class UserState:
    mode: Mode = Mode.IDLE
    session_id: int | None = None
    current_question: dict | None = None
    current_category: str | None = None
    # 모의고사용
    mock_questions: list[dict] = field(default_factory=list)
    mock_index: int = 0

    def reset(self) -> None:
        self.mode = Mode.IDLE
        self.session_id = None
        self.current_question = None
        self.current_category = None
        self.mock_questions = []
        self.mock_index = 0


# user_id → UserState
_states: dict[int, UserState] = {}


def get_state(user_id: int) -> UserState:
    if user_id not in _states:
        _states[user_id] = UserState()
    return _states[user_id]


def clear_state(user_id: int) -> None:
    _states.pop(user_id, None)
