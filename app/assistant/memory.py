"""对话历史管理 — 把每次对话存进数据库，下次请求时拼回给 LLM

LLM 本身不记事儿，每次请求都是独立的。
需要把历史对话存下来，下次当上下文拼进去，LLM 才能"记得"刚才说过什么。
"""

from app import get_db


def add_message(session_id, table_id, role, content, round=0):
    """追加一条对话记录到数据库"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute(
            "INSERT INTO conversations (session_id, table_id, role, content, round) VALUES (?,?,?,?,?)",
            (session_id, table_id, role, content, round),
        )
        db.commit()
    finally:
        db.close()


def get_history(session_id, limit=20, table_id=None):
    """取最近 N 条对话历史，按 session_id 和可选 table_id 过滤"""
    db = get_db()
    try:
        cur = db.cursor()
        if table_id:
            cur.execute(
                "SELECT role, content FROM conversations WHERE session_id=? AND table_id=? ORDER BY id DESC LIMIT ?",
                (session_id, table_id, limit),
            )
        else:
            cur.execute(
                "SELECT role, content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            )
        rows = cur.fetchall()
        rows.reverse()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
    finally:
        db.close()


def clear_history(session_id):
    """清空某个会话的全部历史"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("DELETE FROM conversations WHERE session_id=?", (session_id,))
        db.commit()
    finally:
        db.close()
