"""后厨助手 API 路由"""
import json
import uuid
import time
from flask import Blueprint, request, jsonify, Response, session, stream_with_context
from app.assistant.kitchen_tools import get_kitchen_tools, execute_kitchen_tool, set_event_callback
from app.assistant.kitchen_prompts import KITCHEN_SYSTEM_PROMPT
from app.assistant.agent import Agent
from app.assistant.memory import add_message, get_history, clear_history

bp = Blueprint("kitchen", __name__, url_prefix="/api/kitchen")

# 全局厨房 Agent 实例
_kitchen_agent = None

# 通知事件队列（进程内存），key=table_id, value=list of events
_notification_queues = {}


def _find_customer_session(table_id):
    """通过 table_id 查找该桌最近的顾客对话 session_id"""
    from app import get_db
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT session_id FROM conversations
            WHERE table_id=? AND role='user'
            ORDER BY created_at DESC LIMIT 1
        """, (table_id,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        db.close()


def push_notification(event_type, data):
    """状态变更通知（供厨房工具调用）。data 中可含 table_id 用于路由到对应桌位"""
    tid = data.get("table_id") if isinstance(data, dict) else None
    if tid:
        tid = int(tid)
        if tid not in _notification_queues:
            _notification_queues[tid] = []

        # 生成给顾客的消息文本
        message = None
        if event_type == "items_done":
            message = "您好！您点的菜已全部出餐，请享用！"
        elif event_type == "item_updated":
            status = data.get("status", "")
            if status == "制作中":
                item_name = data.get("item_name", "")
                message = f"您好！{item_name}已开始制作，请稍候~" if item_name else "您好！后厨已开始制作您的菜品，请稍候~"
            elif status == "已出餐":
                item_name = data.get("item_name", "")
                message = f"您好！{item_name}已出餐，请慢用！" if item_name else "您好！您的菜品已出餐，请慢用！"
            elif status == "已上菜":
                message = "您好！您点的菜已全部上齐，请慢用！"
        elif event_type == "item_voided":
            reason = data.get("reason", "")
            message = f"您好！{reason}，已为您处理。"

        # 写入顾客对话历史
        if message:
            from app.assistant.memory import add_message
            sid = _find_customer_session(tid)
            if sid:
                add_message(sid, tid, "assistant", message)

        # 推 SSE
        event_data = {
            "type": event_type, "data": data, "time": time.time(), "message": message,
        }
        _notification_queues[tid].append(event_data)


def _get_agent():
    global _kitchen_agent
    if _kitchen_agent is None:
        from flask import current_app
        _kitchen_agent = Agent(
            api_key=current_app.config["DEEPSEEK_API_KEY"],
            model=current_app.config["LLM_MODEL"],
            base_url=current_app.config["LLM_BASE_URL"],
            tools=get_kitchen_tools(),
            system_prompt=KITCHEN_SYSTEM_PROMPT,
            execute_fn=execute_kitchen_tool,
        )
    return _kitchen_agent


def _get_session_id():
    if "kitchen_sid" not in session:
        session["kitchen_sid"] = uuid.uuid4().hex
    return session["kitchen_sid"]


@bp.route("/chat", methods=["POST"])
def chat():
    """厨房 Agent 对话接口（需 admin 登录）"""
    if "admin_logged_in" not in session:
        return jsonify({"error": "请先登录"}), 401

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
    )
    return jsonify({"reply": reply})


@bp.route("/history", methods=["GET"])
def history():
    """获取厨房会话历史"""
    if "admin_logged_in" not in session:
        return jsonify({"error": "请先登录"}), 401
    messages = get_history(_get_session_id())
    return jsonify({"messages": messages})


@bp.route("/clear", methods=["POST"])
def clear():
    """清空厨房会话历史"""
    clear_history(_get_session_id())
    return jsonify({"message": "已清空"})


# ====== 通知系统 (SSE) ======

@bp.route("/notifications/stream")
def notification_stream():
    """SSE 端点：顾客端监听订单状态变化
    客户端用 EventSource 连接：/api/kitchen/notifications/stream?table_id=X
    """
    table_id = request.args.get("table_id")
    if not table_id:
        return "table_id required", 400

    def generate():
        last_check = time.time()
        tid = int(table_id)
        if tid not in _notification_queues:
            _notification_queues[tid] = []

        while True:
            queue = _notification_queues.get(tid, [])
            new_events = [e for e in queue if e["time"] > last_check]
            for event in new_events:
                yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
            last_check = time.time()
            time.sleep(2)
            yield ": heartbeat\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# 注册通知回调，让厨房工具在状态变更时通知顾客
set_event_callback(push_notification)
