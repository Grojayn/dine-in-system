"""工具定义（JSON Schema）+ 工具执行分发

职责：告诉 LLM 有哪些函数可用，以及当 LLM 说要调某个函数时实际去执行它。
"""

import uuid
from app import models


def get_tools():
    """返回工具定义列表（OpenAI Function Calling 格式）

    LLM 看到这份 JSON 就知道自己能调用哪些函数了。
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_categories",
                "description": "获取所有菜品分类列表",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_dishes_by_category",
                "description": "根据分类ID获取该分类下的所有可售菜品",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category_id": {
                            "type": "integer",
                            "description": "分类ID，如 1=招牌热菜, 2=精致凉菜",
                        },
                    },
                    "required": ["category_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_menu",
                "description": "按关键词搜索可售菜品（名称或描述中包含关键词）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词，如'辣'、'鸡'、'汤'",
                        },
                    },
                    "required": ["keyword"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_dish_detail",
                "description": "获取单个菜品的详细信息（价格、描述、库存等）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "integer", "description": "菜品ID"},
                    },
                    "required": ["item_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "recommend_dishes",
                "description": "根据人数和口味偏好推荐菜品，每次推荐 3-5 道",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "people_count": {
                            "type": "integer",
                            "description": "用餐人数",
                        },
                        "preferences": {
                            "type": "string",
                            "description": "口味偏好，如'辣的'、'清淡'、'荤菜'",
                        },
                        "avoid": {
                            "type": "string",
                            "description": "忌口，如'不吃辣'、'不要香菜'",
                        },
                    },
                    "required": ["people_count"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_table_info",
                "description": "获取当前桌位的信息（桌号、容量、状态）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_number": {
                            "type": "string",
                            "description": "桌号，如 A01",
                        },
                    },
                    "required": ["table_number"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_active_order",
                "description": "获取当前桌位正在进行中的订单信息（菜品、进度、金额）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_id": {
                            "type": "integer",
                            "description": "桌位ID",
                        },
                    },
                    "required": ["table_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "preview_order",
                "description": "预览订单——按菜品名称生成订单预览（不实际提交），然后展示给顾客。顾客确认后调用 confirm_order（confirm_order 不需要额外参数）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "description": "菜品列表（使用菜品名称，不要用ID，名称从 search_menu 的结果中获取）",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "菜品名称，如'鱼香肉丝'",
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "description": "数量",
                                    },
                                    "remark": {
                                        "type": "string",
                                        "description": "单品备注（可选）",
                                    },
                                },
                                "required": ["name", "quantity"],
                            },
                        },
                        "note": {
                            "type": "string",
                            "description": "订单整体备注（可选）",
                        },
                    },
                    "required": ["items"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "confirm_order",
                "description": "确认并提交订单——仅当顾客明确说'确认'/'是的'后才能调用。不需要参数，会自动匹配之前 preview_order 生成的草稿。提交后不可撤销",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "rush_order",
                "description": "催单——标记当前桌位的订单为加急，后厨会优先处理",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_item",
                "description": "取消当前订单中的某个菜品（退菜），顾客说'不要了'/'退菜'时调用。调用后自动通知后厨和回滚库存",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string", "description": "要取消的菜品名称，如'鱼香肉丝'"},
                        "quantity": {"type": "integer", "description": "取消数量，默认 1"},
                    },
                    "required": ["item_name"],
                },
            },
        },
    ]


def execute_tool(name, args, table_id=None, session_id=None):
    """执行 LLM 发起的工具调用

    参数：
        name: 工具名（对应 get_tools 定义的 name）
        args: 工具参数字典
        table_id: 当前桌位ID（由 session 上下文传入，某些工具需要）
        session_id: 当前会话ID（用于暂存草稿）
    返回：
        可 JSON 序列化的结果数据
    """
    if name == "get_categories":
        cats = models.get_categories()
        return [{"id": c["category_id"], "name": c["name"]} for c in cats]

    elif name == "get_dishes_by_category":
        dishes = models.get_menu_by_category(args["category_id"])
        return [
            {
                "id": d["item_id"],
                "name": d["name"],
                "price": d["price"],
                "description": d["description"],
                "category": d["category_name"],
            }
            for d in dishes
        ]

    elif name == "search_menu":
        results = models.search_menu_items(args["keyword"])
        return [
            {
                "id": d["item_id"],
                "name": d["name"],
                "price": d["price"],
                "description": d["description"],
                "category": d["category_name"],
            }
            for d in results
        ]

    elif name == "get_dish_detail":
        dish = models.get_menu_item(args["item_id"])
        if dish:
            return {
                "id": dish["item_id"],
                "name": dish["name"],
                "price": dish["price"],
                "description": dish["description"],
                "is_available": bool(dish["is_available"]),
            }
        return {"error": "未找到该菜品"}

    elif name == "recommend_dishes":
        dishes = models.get_menu_by_category()
        candidates = [d for d in dishes if d["is_recommended"] == 1]
        if not candidates:
            candidates = dishes
        selected = candidates[: min(args.get("people_count", 2) + 2, len(candidates))]
        return [
            {
                "id": d["item_id"],
                "name": d["name"],
                "price": d["price"],
                "description": d["description"],
                "category": d["category_name"],
            }
            for d in selected
        ]

    elif name == "get_table_info":
        table = models.get_table_by_number(args["table_number"])
        if table:
            return {
                "table_id": table["table_id"],
                "table_number": table["table_number"],
                "capacity": table["capacity"],
                "status": table["status"],
            }
        return {"error": "未找到该桌位"}

    elif name == "get_active_order":
        tid = args.get("table_id") or table_id
        if not tid:
            return {"error": "缺少桌位ID"}
        order = models.get_active_order(tid)
        if order:
            details = models.get_order_detail(order["order_id"])
            return {
                "order_id": order["order_id"],
                "order_number": order["order_number"],
                "status": order["status"],
                "total_amount": order["total_amount"],
                "items": [
                    {
                        "name": d["item_name"],
                        "quantity": d["quantity"],
                        "status": d["status"],
                    }
                    for d in details
                ],
            }
        return {"message": "暂无进行中的订单"}

    elif name == "preview_order":
        if not table_id:
            return {"error": "缺少桌位ID，无法下单"}

        # 按名称解析菜品，生成预览草稿（不写DB）
        draft_key = f"{table_id}:{session_id}" if session_id else None
        resolved = []
        total = 0.0
        errors = []
        for item in args["items"]:
            results = models.search_menu_items(item["name"])
            info = None
            for r in results:
                if r["name"] == item["name"]:
                    info = r
                    break
            if info is None and results:
                info = results[0]
            if info is None:
                errors.append(f"未找到菜品: {item['name']}")
                continue
            qty = item["quantity"]
            # 库存校验
            stock = info["stock"]
            if stock <= 0:
                errors.append(f"{info['name']} 已售罄")
                continue
            if stock < qty:
                errors.append(f"{info['name']} 库存不足（仅剩 {stock} 份）")
                continue
            subtotal = info["price"] * qty
            total += subtotal
            resolved.append({
                "item_id": info["item_id"],
                "name": info["name"],
                "price": info["price"],
                "quantity": qty,
                "subtotal": subtotal,
                "remark": item.get("remark", ""),
            })

        if errors:
            return {"error": "；".join(errors)}

        # 用 table_id:session_id 做 key，confirm_order 不需要额外参数就能查到
        draft_key = f"{table_id}:{session_id}" if session_id else uuid.uuid4().hex
        models.save_draft(draft_key, table_id, resolved, args.get("note", ""), total)

        return {
            "items": [{"name": i["name"], "price": i["price"], "quantity": i["quantity"], "subtotal": i["subtotal"]} for i in resolved],
            "total": total,
            "message": "请展示给顾客确认，顾客确认后直接调用 confirm_order（无需参数）",
        }

    elif name == "confirm_order":
        draft_key = f"{table_id}:{session_id}" if session_id else None
        if not draft_key or not models.draft_exists(draft_key):
            return {"error": "没有待确认的订单，请先调用 preview_order"}
        draft = models.get_draft(draft_key)
        models.delete_draft(draft_key)
        items_for_db = [
            {"item_id": i["item_id"], "quantity": i["quantity"], "remark": i["remark"]}
            for i in draft["items"]
        ]
        order_id, order_number = models.create_order(draft["table_id"], items_for_db, draft["note"])
        models.deduct_order_stock(items_for_db)
        return {
            "order_id": order_id,
            "order_number": order_number,
            "message": "下单成功",
        }

    elif name == "rush_order":
        if not table_id:
            return {"error": "缺少桌位ID"}
        order = models.get_active_order(table_id)
        if not order:
            return {"error": "暂无进行中的订单"}
        models.rush_order(order["order_id"])
        return {"ok": True, "message": "已标记加急，后厨将优先处理"}

    elif name == "cancel_item":
        if not table_id:
            return {"error": "缺少桌位ID"}
        order = models.get_active_order(table_id)
        if not order:
            return {"error": "暂无进行中的订单"}
        qty = args.get("quantity", 1)
        result = models.cancel_item_in_order(order["order_id"], args["item_name"], qty)
        return result

    return {"error": f"未知工具: {name}"}


_CN_NUM = {'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}


def _parse_order_msg(msg):
    """从用户消息中提取菜品名和数量，如'下单一份水煮鱼片' → ('水煮鱼片', 1)"""
    import re
    # 数字+份模式：2份宫保鸡丁
    m = re.search(r'(\d+)\s*份(.+)', msg)
    if m:
        return m.group(2).strip(), int(m.group(1))
    # 中文数字+份模式：一份宫保鸡丁、两份宫保鸡丁
    m = re.search(r'[一两二三四五六七八九]\s*份(.+)', msg)
    if m:
        qty = _CN_NUM.get(m.group(0)[0], 1)
        return m.group(1).strip(), qty
    # 没数量默认1份
    for kw in ['下单', '点一份', '来一份', '要一份', '帮我']:
        idx = msg.find(kw)
        if idx >= 0:
            name = msg[idx + len(kw):].strip()
            if name:
                return name, 1
    return None, 0


def try_preview(table_id, session_id, user_msg):
    """路由层直接调用的预览下单函数，解析消息并生成订单草稿"""
    name, qty = _parse_order_msg(user_msg)
    if not name:
        return False, None
    results = models.search_menu_items(name)
    info = None
    for r in results:
        if name in r["name"]:
            info = r
            break
    if not info and results:
        info = results[0]
    if not info:
        return False, None
    if info["stock"] <= 0:
        return True, {"error": f"{info['name']} 已售罄", "items": []}
    qty = min(qty, info["stock"])
    items = [{"item_id": info["item_id"], "name": info["name"], "price": info["price"],
              "quantity": qty, "subtotal": info["price"] * qty, "remark": ""}]
    total = sum(i["subtotal"] for i in items)
    draft_key = f"{table_id}:{session_id}"
    models.save_draft(draft_key, table_id, items, "", total)
    return True, {"items": [{"name": i["name"], "price": i["price"], "quantity": i["quantity"],
                             "subtotal": i["subtotal"]} for i in items], "total": total}


def try_confirm(table_id, session_id):
    """路由层直接调用的确认下单函数（不走 LLM）"""
    draft_key = f"{table_id}:{session_id}" if session_id else None
    if not draft_key or not models.draft_exists(draft_key):
        return False, ""
    draft = models.get_draft(draft_key)
    models.delete_draft(draft_key)
    items_for_db = [
        {"item_id": i["item_id"], "quantity": i["quantity"], "remark": i.get("remark", "")}
        for i in draft["items"]
    ]
    order_id, order_number = models.create_order(draft["table_id"], items_for_db, draft["note"])
    models.deduct_order_stock(items_for_db)
    names = [f"{i['name']}x{i['quantity']}" for i in draft["items"]]
    msg = f"下单成功！{'、'.join(names)}。订单号：{order_number}"
    return True, msg
