import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path


# 根据当前文件位置定位数据库，避免受运行工作目录影响
DB_PATH = Path(__file__).resolve().parent / "chat_history.sqlite3"


@contextmanager
def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        # 正常结束提交，发生异常回滚
        with connection:
            yield connection
    finally:
        connection.close()


# 创建表结构
def init_db():
    """初始化数据库。已有表不会被清空。"""
    with connect_db() as connection:
        # 创建会话表
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建消息表
        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL
                    CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES conversations(id)
            )
        """)

        # 创建索引
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, id)
        """)
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(conversations)")}
        if "title_is_custom" not in columns:
            connection.execute(
                "ALTER TABLE conversations ADD COLUMN title_is_custom INTEGER NOT NULL DEFAULT 0"
            )
        message_columns = {row["name"] for row in connection.execute("PRAGMA table_info(messages)")}
        if "sources_json" not in message_columns:
            connection.execute("ALTER TABLE messages ADD COLUMN sources_json TEXT NOT NULL DEFAULT '[]'")


def create_conversation():
    """创建新对话，返回唯一的会话 ID。"""
    session_id = str(uuid.uuid4())

    with connect_db() as connection:
        connection.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (session_id, "新对话"),
        )

    return session_id


def list_conversations():
    """读取历史对话列表，新建的排在前面。"""
    with connect_db() as connection:
        rows = connection.execute("""
            SELECT id, title
            FROM conversations
            ORDER BY created_at DESC, rowid DESC
        """).fetchall()

    return [dict(row) for row in rows]


def load_messages(session_id):
    """只读取指定会话的消息，并保持原来的顺序。"""
    with connect_db() as connection:
        rows = connection.execute(
            """
            SELECT role, content, sources_json
            FROM messages
            WHERE session_id = ?
            ORDER BY id
            """,
            (session_id,),
        ).fetchall()

    return [
        {"role": row["role"], "content": row["content"], "sources": json.loads(row["sources_json"])}
        for row in rows
    ]


def rename_conversation(session_id, title):
    """修改标题；手动标题不再被首条问题覆盖。"""
    title = title.strip()
    if not title or len(title) > 100:
        raise ValueError("标题须为1到100个字符，不能全为空格。")
    with connect_db() as connection:
        cursor = connection.execute(
            "UPDATE conversations SET title = ?, title_is_custom = 1 WHERE id = ?",
            (title, session_id),
        )
        if cursor.rowcount == 0:
            raise ValueError("该对话已不存在，请刷新页面。")


def delete_conversation(session_id):
    """在同一事务中删除指定会话及其消息，不影响其他会话。"""
    with connect_db() as connection:
        connection.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        connection.execute("DELETE FROM conversations WHERE id = ?", (session_id,))


def save_message(session_id, role, content, sources=None):
    """保存一条消息，第一条用户消息同时用作会话标题。"""
    if role not in ("user", "assistant"):
        raise ValueError("不支持的消息角色")

    if not isinstance(content, str) or not content.strip():
        raise ValueError("消息内容不能为空")

    with connect_db() as connection:
        connection.execute(
            """
            INSERT INTO messages (session_id, role, content, sources_json)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, json.dumps(sources or [], ensure_ascii=False)),
        )

        if role == "user":
            user_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM messages
                WHERE session_id = ? AND role = 'user'
                """,
                (session_id,),
            ).fetchone()[0]

            if user_count == 1:
                title = " ".join(content.split())[:24]
                connection.execute(
                    "UPDATE conversations SET title = ? WHERE id = ? AND title_is_custom = 0",
                    (title, session_id),
                )
