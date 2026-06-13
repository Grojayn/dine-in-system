"""厨房 Agent 工具定义 + 执行分发"""

from app import models

# 事件通知回调（由 routes/kitchen.py 注入）
_on_event = None

# 工具调用追踪（调试用）
_tool_trace = []

def get_tool_trace():
    return list(_tool_trace)

def clear_tool_trace():
    _tool_trace.clear()


def set_event_callback(fn):
    global _on_event
    _on_event = fn


def _notify(event_type, data):
    if _on_event:
        _on_event(event_type, data)


def _lookup_table_id_for_detail(detail_id):
    """通过 detail_id 查找所属桌位"""
    from app import get_db
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT o.table_id FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE oi.detail_id = ?
        """, (detail_id,))
        row = cur.fetchone()
        return row["table_id"] if row else None
    finally:
        db.close()


def _lookup_table_ids_for_details(detail_ids):
    """批量查找 detail_id 所属桌位"""
    if not detail_ids:
        return set()
    from app import get_db
    db = get_db()
    try:
        cur = db.cursor()
        placeholders = ",".join("?" for _ in detail_ids)
        cur.execute(f"""
            SELECT DISTINCT o.table_id FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE oi.detail_id IN ({placeholders})
        """, detail_ids)
        return {row["table_id"] for row in cur.fetchall()}
    finally:
        db.close()


def get_kitchen_tools():
    """返回厨房工具定义列表（OpenAI Function Calling 格式）"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_kitchen_dashboard",
                "description": "查看厨房概览：待处理订单数、待制作菜品数、库存预警",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pending_orders",
                "description": "查看所有待处理订单列表（未结账的），含桌号、订单金额",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_aggregated_dishes",
                "description": "按菜品聚合查看所有待制作菜品（合并相同菜品）。后厨最常用的功能，用于决定先做什么菜",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_detail",
                "description": "查看某个订单的详细信息（菜品列表、数量、状态、备注）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "integer", "description": "订单ID"},
                    },
                    "required": ["order_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_item_status",
                "description": "更新单个菜品的制作状态",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detail_id": {"type": "integer", "description": "订单项ID（从 get_order_detail 或 get_aggregated_dishes 获取）"},
                        "status": {"type": "string", "enum": ["制作中", "待出餐", "已出餐"], "description": "目标状态"},
                    },
                    "required": ["detail_id", "status"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "batch_mark_done",
                "description": "批量将多个菜品标记为已出餐（一次性出多道菜时用）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detail_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "订单项ID列表",
                        },
                    },
                    "required": ["detail_ids"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_menu_items",
                "description": "按名称搜索菜品，返回菜品信息（ID、名称、价格、库存）。后厨需修改库存或查看某个具体菜品时先用此工具找到菜品ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "搜索关键词，如'鸡'、'口水鸡'"},
                    },
                    "required": ["keyword"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_stock",
                "description": "查看某个菜品的当前库存",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "integer", "description": "菜品ID（从 search_menu_items 或 get_aggregated_dishes 获取）"},
                    },
                    "required": ["item_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "void_item",
                "description": "退菜/做错菜处理：从订单移除、回滚库存、记录损耗",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "detail_id": {"type": "integer", "description": "订单项ID"},
                        "reason": {"type": "string", "description": "退菜原因，如'顾客不要了'、'做错了'"},
                    },
                    "required": ["detail_id", "reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "update_stock",
                "description": "修改某个菜品的库存数量（覆盖式设置）。适用于补货或盘点调整",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "integer", "description": "菜品ID"},
                        "stock": {"type": "integer", "description": "新的库存数量"},
                    },
                    "required": ["item_id", "stock"],
                },
            },
        },
    ]


def execute_kitchen_tool(name, args, table_id=None, session_id=None):
    """执行厨房 LLM 发起的工具调用"""
    _tool_trace.append({"name": name, "args": args})
    if name == "get_kitchen_dashboard":
        stats = models.get_kitchen_dashboard_stats()
        orders = models.get_kitchen_orders()
        # 所有菜品库存清单，便于搜索
        all_items = models.get_all_menu_items()
        return {
            "stats": {
                "pending_orders": stats["total_pending_orders"],
                "pending_items": stats["total_pending_items"],
                "dishes_count": stats["dishes_count"],
                "stock_alerts": stats["stock_alerts"],
            },
            "recent_orders": [
                {
                    "order_id": o["order_id"],
                    "table_number": o["table_number"],
                    "status": o["status"],
                    "total_amount": o["total_amount"],
                    "created_at": o["created_at"],
                }
                for o in orders[:10]
            ],
            "all_menu_items": [
                {"item_id": m["item_id"], "name": m["name"], "price": m["price"], "stock": m["stock"], "category": m["category_name"]}
                for m in all_items
            ],
        }

    elif name == "get_pending_orders":
        orders = models.get_kitchen_orders()
        return [
            {
                "order_id": o["order_id"],
                "order_number": o["order_number"],
                "table_number": o["table_number"],
                "status": o["status"],
                "total_amount": o["total_amount"],
                "created_at": o["created_at"],
            }
            for o in orders
        ]

    elif name == "get_aggregated_dishes":
        dishes = models.get_kitchen_items_by_dish()
        return [
            {
                "item_id": d["item_id"],
                "item_name": d["name"],
                "total_quantity": d["total_pending"],
                "order_count": len(d["items"]),
                "details": d["items"],
            }
            for d in dishes
        ]

    elif name == "get_order_detail":
        order = models.get_order_info(args["order_id"])
        if not order:
            return {"error": "未找到该订单"}
        items = models.get_order_detail(args["order_id"])
        return {
            "order_id": order["order_id"],
            "order_number": order["order_number"],
            "table_number": order["table_number"],
            "status": order["status"],
            "total_amount": order["total_amount"],
            "note": order["note"],
            "created_at": order["created_at"],
            "items": [
                {
                    "detail_id": i["detail_id"],
                    "item_name": i["item_name"],
                    "quantity": i["quantity"],
                    "status": i["status"],
                    "remark": i["remark"],
                }
                for i in items
            ],
        }

    elif name == "update_item_status":
        count = models.batch_update_item_status([args["detail_id"]], args["status"])
        if count == 0:
            return {"error": "未找到该订单项"}
        tid = _lookup_table_id_for_detail(args["detail_id"])
        # 查菜品名称用于通知
        item_name = ""
        d = None
        try:
            from app import get_db as _get_db
            d = _get_db()
            row = d.execute("SELECT mi.name FROM order_items oi JOIN menu_items mi ON oi.item_id=mi.item_id WHERE oi.detail_id=?", (args["detail_id"],)).fetchone()
            item_name = row[0] if row else ""
        finally:
            if d: d.close()
        _notify("item_updated", {
            "detail_id": args["detail_id"],
            "status": args["status"],
            "table_id": tid,
            "item_name": item_name,
        })
        return {"ok": True, "message": f"已更新为 {args['status']}"}

    elif name == "batch_mark_done":
        count = models.batch_update_item_status(args["detail_ids"], "已出餐")
        # 批量出餐要扣库存
        from app import get_db
        db = get_db()
        try:
            cur = db.cursor()
            placeholders = ",".join("?" for _ in args["detail_ids"])
            cur.execute(
                f"SELECT item_id, quantity FROM order_items WHERE detail_id IN ({placeholders})",
                args["detail_ids"],
            )
            for row in cur.fetchall():
                models.deduct_stock(row["item_id"], row["quantity"])
        finally:
            db.close()
        # 通知所有受影响的桌位
        tids = _lookup_table_ids_for_details(args["detail_ids"])
        for tid in tids:
            _notify("items_done", {
                "detail_ids": args["detail_ids"],
                "table_id": tid,
                "message": f"已完成 {count} 道菜品出餐",
            })
        return {"ok": True, "updated_count": count, "message": f"已完成 {count} 道菜品出餐"}

    elif name == "search_menu_items":
        results = models.search_menu_items(args["keyword"])
        return [
            {
                "item_id": d["item_id"],
                "name": d["name"],
                "price": d["price"],
                "stock": d["stock"],
                "category": d["category_name"],
            }
            for d in results
        ]

    elif name == "check_stock":
        stock = models.get_item_stock(args["item_id"])
        return {"item_id": args["item_id"], "stock": stock}

    elif name == "void_item":
        tid = _lookup_table_id_for_detail(args["detail_id"])
        result = models.void_order_item(args["detail_id"], args["reason"])
        if not result.get("ok"):
            return {"error": result.get("message", "退菜失败")}
        _notify("item_voided", {
            "detail_id": args["detail_id"],
            "reason": args["reason"],
            "table_id": tid,
        })
        return result

    elif name == "update_stock":
        models.update_stock(args["item_id"], args["stock"])
        from app import get_db
        db_instance = get_db()
        cur = db_instance.cursor()
        cur.execute("SELECT name FROM menu_items WHERE item_id=?", (args["item_id"],))
        row = cur.fetchone()
        name = row["name"] if row else f"ID={args['item_id']}"
        db_instance.close()
        return {"ok": True, "message": f"{name} 库存已改为 {args['stock']}"}

    return {"error": f"未知工具: {name}"}
