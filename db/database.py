"""SQLite 기반 유저 세션 및 학습 기록 관리"""
import json
import aiosqlite
from datetime import datetime
from config import DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                joined_at   TEXT NOT NULL,
                total_attempts INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                mode        TEXT NOT NULL,   -- 'practice' | 'mock'
                started_at  TEXT NOT NULL,
                ended_at    TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS attempts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                session_id      INTEGER,
                question_id     TEXT NOT NULL,
                question_text   TEXT NOT NULL,
                answer_type     TEXT NOT NULL,  -- 'text' | 'voice'
                answer_text     TEXT,           -- STT 결과 or 직접 입력
                score           TEXT,           -- 'AL'|'IH'|'IM'|'IL'|'NH' 등
                feedback        TEXT,           -- AI 피드백 전체 (JSON)
                attempted_at    TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS user_mistakes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                error_type  TEXT NOT NULL,  -- 'tense'|'vocabulary'|'fluency' 등
                example     TEXT NOT NULL,
                corrected   TEXT NOT NULL,
                noted_at    TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
        """)
        await db.commit()


async def upsert_user(user_id: int, username: str, first_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, joined_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name
        """, (user_id, username, first_name, datetime.utcnow().isoformat()))
        await db.commit()


async def start_session(user_id: int, mode: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO sessions (user_id, mode, started_at) VALUES (?, ?, ?)
        """, (user_id, mode, datetime.utcnow().isoformat()))
        await db.commit()
        return cursor.lastrowid


async def end_session(session_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE sessions SET ended_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), session_id)
        )
        await db.commit()


async def save_attempt(
    user_id: int,
    session_id: int | None,
    question_id: str,
    question_text: str,
    answer_type: str,
    answer_text: str,
    score: str,
    feedback: dict,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO attempts
              (user_id, session_id, question_id, question_text, answer_type, answer_text, score, feedback, attempted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, session_id, question_id, question_text,
            answer_type, answer_text, score,
            json.dumps(feedback, ensure_ascii=False),
            datetime.utcnow().isoformat()
        ))
        await db.execute(
            "UPDATE users SET total_attempts = total_attempts + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_recent_mistakes(user_id: int, limit: int = 5) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT error_type, example, corrected, noted_at
            FROM user_mistakes
            WHERE user_id = ?
            ORDER BY noted_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def save_mistake(user_id: int, error_type: str, example: str, corrected: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO user_mistakes (user_id, error_type, example, corrected, noted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, error_type, example, corrected, datetime.utcnow().isoformat()))
        await db.commit()


async def get_user_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT u.total_attempts,
                   COUNT(DISTINCT s.id) as total_sessions,
                   MAX(a.attempted_at) as last_attempt
            FROM users u
            LEFT JOIN sessions s ON s.user_id = u.user_id
            LEFT JOIN attempts a ON a.user_id = u.user_id
            WHERE u.user_id = ?
            GROUP BY u.user_id
        """, (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else {}
