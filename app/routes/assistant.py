"""智能点餐助手 API 路由

把 Agent 引擎包装成 HTTP 接口，供前端聊天组件调用。
"""

import uuid
import json
from flask import Blueprint, request, jsonify, session
from app.assistant import Agent, get_history, clear_history

bp = Blueprint("assistant", __name__, url_prefix="/api/assistant")

# 全局 Agent 实例（进程生命周期内复用）
_agent = None


def _get_agent():
    global _agent
    if _agent is None:
        from flask import current_app
        _agent = Agent(
            api_key=current_app.config["DEEPSEEK_API_KEY"],
            model=current_app.config["LLM_MODEL"],
            base_url=current_app.config["LLM_BASE_URL"],
        )
    return _agent


def _get_session_id():
    """获取或创建当前浏览器的会话ID"""
    if "assistant_sid" not in session:
        session["assistant_sid"] = uuid.uuid4().hex
    return session["assistant_sid"]


@bp.route("/chat", methods=["POST"])
def chat():
    """接收用户消息，返回 Agent 回复"""
    if "table_id" not in session:
        return jsonify({"error": "请先选择桌位"}), 400

    data = request.get_json(silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "缺少 message 参数"}), 400

    user_msg = data["message"].strip()
    if not user_msg:
        return jsonify({"error": "消息不能为空"}), 400

    agent = _get_agent()
    reply = agent.process_message(
        user_msg=user_msg,
        session_id=_get_session_id(),
        table_id=session["table_id"],
        table_number=session.get("table_number", ""),
    )

    return jsonify({"reply": reply})


@bp.route("/history", methods=["GET"])
def history():
    """获取当前会话的历史消息"""
    if "table_id" not in session:
        return jsonify({"error": "请先选择桌位"}), 400

    messages = get_history(_get_session_id(), table_id=session.get("table_id"))
    return jsonify({"messages": messages})


@bp.route("/clear", methods=["POST"])
def clear():
    """清空当前会话的历史"""
    clear_history(_get_session_id())
    return jsonify({"message": "已清空"})
