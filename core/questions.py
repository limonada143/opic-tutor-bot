"""문제 뱅크 로딩 및 랜덤 추출"""
import json
import random
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent / "data" / "questions.json"
_bank: dict = {}


def load_questions() -> None:
    global _bank
    with open(_DATA_PATH, encoding="utf-8") as f:
        _bank = json.load(f)


def get_categories() -> dict[str, str]:
    """카테고리 id → label 매핑 반환"""
    return {k: v["label"] for k, v in _bank.get("categories", {}).items()}


def get_random_question(category: str) -> dict | None:
    """카테고리에서 랜덤 문제 1개 반환. 없으면 None."""
    questions = _bank.get("categories", {}).get(category, {}).get("questions", [])
    if not questions:
        return None
    return random.choice(questions)


def get_mock_exam_questions() -> list[dict]:
    """모의고사 15문항 큐레이션 (template 기반)"""
    result = []
    template = _bank.get("mock_exam_template", {}).get("structure", [])
    for slot in template:
        cat = slot["category"]
        count = slot["count"]
        pool = _bank.get("categories", {}).get(cat, {}).get("questions", [])
        chosen = random.sample(pool, min(count, len(pool)))
        result.extend(chosen)
    return result


def count_questions() -> dict[str, int]:
    """카테고리별 문제 수 반환"""
    return {
        k: len(v.get("questions", []))
        for k, v in _bank.get("categories", {}).items()
    }
