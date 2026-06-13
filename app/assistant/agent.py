"""Agent 引擎 — 核心对话循环

这是整个 Agent 的大脑，负责：
1. 拼装 messages（system prompt + 历史 + 当前问题）
2. 调 LLM 接口
3. 如果 LLM 返回工具调用 → 执行 → 结果回传 → 直到 LLM 给出最终回复
4. 存历史 → 返回回复
"""

import json
from openai import OpenAI

from .tools import get_tools, execute_tool
from .prompts import SYSTEM_PROMPT
from .memory import add_message, get_history


class Agent:
    """LLM 驱动的 Agent，具备 Function Calling 能力"""

    def __init__(self, api_key, model="deepseek-chat", base_url="https://api.deepseek.com",
                 tools=None, system_prompt=None, execute_fn=None):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self._tools = tools
        self._system_prompt = system_prompt
        self._execute_fn = execute_fn

    def process_message(self, user_msg, session_id, table_id=None, table_number=""):
        """处理一条用户消息，经过工具循环后返回最终回复"""

        # ① 组装 system prompt（支持自定义）
        system_prompt = self._system_prompt if self._system_prompt is not None else SYSTEM_PROMPT
        system_prompt = system_prompt.format(table_number=table_number)

        # ② 取对话历史
        history = get_history(session_id, table_id=table_id)

        # ③ 组装完整 messages 列表
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_msg})

        current_round = len(history) // 2 + 1
        add_message(session_id, table_id, "user", user_msg, round=current_round)

        # ④ 工具调用循环
        tools = self._tools if self._tools is not None else get_tools()
        execute_fn = self._execute_fn or execute_tool
        for turn in range(5):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            if not msg.tool_calls:
                reply = msg.content or ""
                add_message(session_id, table_id, "assistant", reply, round=current_round)
                return reply

            messages.append(msg)

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    fn_args = {}

                try:
                    result = execute_fn(fn_name, fn_args, table_id=table_id, session_id=session_id)
                except Exception as e:
                    result = {"error": f"执行 {fn_name} 时出错: {str(e)}"}
                # debug：追踪 LLM 工具调用
                try:
                    f = open("agent_trace.log","a")
                    f.write(f"[TOOL] turn={turn} name={fn_name} args={fn_args}\n")
                    f.close()
                except:
                    pass

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        fallback = "抱歉，我暂时无法处理您的请求，请稍后再试。"
        add_message(session_id, table_id, "assistant", fallback, round=current_round)
        return fallback
