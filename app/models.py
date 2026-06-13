import sqlite3
import json
from datetime import datetime
from app import get_db

def get_categories():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT * FROM categories ORDER BY sort_order")
        return cur.fetchall()
    finally:
        db.close()

def add_category(name, sort_order=0):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO categories (name, sort_order) VALUES (?, ?)", (name, sort_order))
        db.commit()
    finally:
        db.close()

def update_category(cid, name, sort_order=0):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("UPDATE categories SET name=?, sort_order=? WHERE category_id=?", (name, sort_order, cid))
        db.commit()
    finally:
        db.close()

def delete_category(cid):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("DELETE FROM categories WHERE category_id=?", (cid,))
        db.commit()
    finally:
        db.close()

def get_menu_by_category(category_id=None):
    db = get_db()
    try:
        cur = db.cursor()
        if category_id:
            cur.execute("SELECT m.*, c.name as category_name FROM menu_items m JOIN categories c ON m.category_id=c.category_id WHERE m.category_id=? AND m.is_available=1 ORDER BY m.item_id", (category_id,))
        else:
            cur.execute("SELECT m.*, c.name as category_name FROM menu_items m JOIN categories c ON m.category_id=c.category_id WHERE m.is_available=1 ORDER BY c.sort_order, m.item_id")
        return cur.fetchall()
    finally:
        db.close()

def get_all_menu_items():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT m.*, c.name as category_name FROM menu_items m JOIN categories c ON m.category_id=c.category_id ORDER BY c.sort_order, m.item_id")
        return cur.fetchall()
    finally:
        db.close()

def get_menu_item(item_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT * FROM menu_items WHERE item_id=?", (item_id,))
        return cur.fetchone()
    finally:
        db.close()

def search_menu_items(keyword):
    db = get_db()
    try:
        cur = db.cursor()
        pattern = f"%{keyword}%"
        cur.execute("SELECT m.*, c.name as category_name FROM menu_items m JOIN categories c ON m.category_id=c.category_id WHERE m.is_available=1 AND (m.name LIKE ? OR m.description LIKE ?) ORDER BY m.item_id", (pattern, pattern))
        return cur.fetchall()
    finally:
        db.close()

def add_menu_item(category_id, name, price, description="", is_recommended=0, stock=50):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO menu_items (category_id, name, price, description, is_recommended, stock) VALUES (?,?,?,?,?,?)",
                   (category_id, name, price, description, is_recommended, stock))
        db.commit()
    finally:
        db.close()

def update_menu_item(item_id, category_id, name, price, description, is_available, is_recommended, stock=None):
    db = get_db()
    try:
        cur = db.cursor()
        if stock is not None:
            cur.execute("UPDATE menu_items SET category_id=?, name=?, price=?, description=?, is_available=?, is_recommended=?, stock=? WHERE item_id=?",
                       (category_id, name, price, description, is_available, is_recommended, stock, item_id))
        else:
            cur.execute("UPDATE menu_items SET category_id=?, name=?, price=?, description=?, is_available=?, is_recommended=? WHERE item_id=?",
                       (category_id, name, price, description, is_available, is_recommended, item_id))
        db.commit()
    finally:
        db.close()

def delete_menu_item(item_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("DELETE FROM menu_items WHERE item_id=?", (item_id,))
        db.commit()
    finally:
        db.close()

def get_tables():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT * FROM tables_info ORDER BY table_number")
        return cur.fetchall()
    finally:
        db.close()

def get_table_by_number(table_number):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT * FROM tables_info WHERE table_number=?", (table_number,))
        return cur.fetchone()
    finally:
        db.close()

def update_table_status(tid, status):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("UPDATE tables_info SET status=? WHERE table_id=?", (status, tid))
        db.commit()
    finally:
        db.close()

def add_table(table_number, capacity=4):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("INSERT INTO tables_info (table_number, capacity) VALUES (?, ?)", (table_number, capacity))
        db.commit()
    finally:
        db.close()

def update_table_info(tid, table_number, capacity):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("UPDATE tables_info SET table_number=?, capacity=? WHERE table_id=?", (table_number, capacity, tid))
        db.commit()
    finally:
        db.close()

def delete_table(tid):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("DELETE FROM tables_info WHERE table_id=?", (tid,))
        db.commit()
    finally:
        db.close()

def occupy_table(table_id):
    db = get_db()
    db.execute("UPDATE tables_info SET status='已占用' WHERE table_id=?", (table_id,))
    db.commit()
    db.close()

def create_order(table_id, items, note=""):
    db = get_db()
    try:
        cur = db.cursor()
        import random
        order_number = datetime.now().strftime("OD%Y%m%d%H%M%S") + str(random.randint(100,999))
        total = 0
        for item in items:
            cur.execute("SELECT price FROM menu_items WHERE item_id=?", (item["item_id"],))
            menu = cur.fetchone()
            total += menu["price"] * item["quantity"]
        cur.execute("INSERT INTO orders (table_id, order_number, total_amount, note) VALUES (?,?,?,?)",
                   (table_id, order_number, total, note))
        order_id = cur.lastrowid
        for item in items:
            cur.execute("SELECT price FROM menu_items WHERE item_id=?", (item["item_id"],))
            menu = cur.fetchone()
            subtotal = menu["price"] * item["quantity"]
            cur.execute("INSERT INTO order_items (order_id, item_id, quantity, unit_price, subtotal, remark) VALUES (?,?,?,?,?,?)",
                       (order_id, item["item_id"], item["quantity"], menu["price"], subtotal, item.get("remark", "")))
        cur.execute("UPDATE tables_info SET status='已占用' WHERE table_id=?", (table_id,))
        db.commit()
        return order_id, order_number
    finally:
        db.close()

def get_active_order(table_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT * FROM orders WHERE table_id=? AND status!='已结账' ORDER BY created_at DESC LIMIT 1", (table_id,))
        return cur.fetchone()
    finally:
        db.close()

def get_table_orders(table_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT * FROM orders WHERE table_id=? AND status!='已结账' ORDER BY created_at ASC", (table_id,))
        return cur.fetchall()
    finally:
        db.close()

def get_order_detail(order_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT oi.*, mi.name as item_name FROM order_items oi JOIN menu_items mi ON oi.item_id=mi.item_id WHERE oi.order_id=?", (order_id,))
        return cur.fetchall()
    finally:
        db.close()

def get_order_info(order_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT o.*, t.table_number FROM orders o JOIN tables_info t ON o.table_id=t.table_id WHERE o.order_id=?", (order_id,))
        return cur.fetchone()
    finally:
        db.close()

def pay_order(order_id, table_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("UPDATE orders SET status='已结账', paid_at=datetime('now','localtime') WHERE order_id=?", (order_id,))
        cur.execute("UPDATE tables_info SET status='空闲' WHERE table_id=?", (table_id,))
        cur.execute("DELETE FROM conversations WHERE table_id=?", (table_id,))
        db.commit()
    finally:
        db.close()


def pay_all_orders(table_id):
    """结清某桌所有未结账订单"""
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("UPDATE orders SET status='已结账', paid_at=datetime('now','localtime') WHERE table_id=? AND status!='已结账'", (table_id,))
        cur.execute("UPDATE tables_info SET status='空闲' WHERE table_id=?", (table_id,))
        cur.execute("DELETE FROM conversations WHERE table_id=?", (table_id,))
        db.commit()
    finally:
        db.close()

def get_all_orders():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT o.*, t.table_number FROM orders o JOIN tables_info t ON o.table_id=t.table_id ORDER BY o.created_at DESC")
        return cur.fetchall()
    finally:
        db.close()

def update_order_status(order_id, status):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
        if status == "已上菜":
            cur.execute("UPDATE order_items SET status='已出餐' WHERE order_id=? AND status='制作中'", (order_id,))
        elif status == "已结账":
            cur.execute("SELECT table_id FROM orders WHERE order_id=?", (order_id,))
            tid = cur.fetchone()[0]
            cur.execute("UPDATE tables_info SET status='空闲' WHERE table_id=?", (tid,))
        db.commit()
    finally:
        db.close()

def update_order_item_status(detail_id, status):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("UPDATE order_items SET status=? WHERE detail_id=?", (status, detail_id))
        db.commit()
    finally:
        db.close()

def verify_admin(username, password):
    from werkzeug.security import check_password_hash
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT * FROM admins WHERE username=?", (username,))
        admin = cur.fetchone()
        if admin:
            return check_password_hash(admin['password'], password)
        return False
    finally:
        db.close()


# ========== 厨房助手：库存 ==========

def get_item_stock(item_id):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT stock FROM menu_items WHERE item_id=?", (item_id,))
        row = cur.fetchone()
        return row["stock"] if row else 0
    finally:
        db.close()


def deduct_stock(item_id, quantity):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT stock FROM menu_items WHERE item_id=?", (item_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"菜品 {item_id} 不存在")
        if row["stock"] < quantity:
            raise ValueError(f"库存不足：当前 {row['stock']}，需要 {quantity}")
        cur.execute("UPDATE menu_items SET stock = stock - ? WHERE item_id=?", (quantity, item_id))
        db.commit()
        return row["stock"] - quantity
    finally:
        db.close()


def restore_stock(item_id, quantity):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("UPDATE menu_items SET stock = stock + ? WHERE item_id=?", (quantity, item_id))
        db.commit()
    finally:
        db.close()


def check_items_stock(items):
    db = get_db()
    try:
        cur = db.cursor()
        details = []
        for item in items:
            cur.execute("SELECT name, stock FROM menu_items WHERE item_id=?", (item["item_id"],))
            row = cur.fetchone()
            if row:
                details.append({
                    "item_id": item["item_id"],
                    "name": row["name"],
                    "stock": row["stock"],
                    "required": item["quantity"],
                    "enough": row["stock"] >= item["quantity"],
                })
            else:
                details.append({
                    "item_id": item["item_id"],
                    "name": "未知",
                    "stock": 0,
                    "required": item["quantity"],
                    "enough": False,
                })
        return {"ok": all(d["enough"] for d in details), "details": details}
    finally:
        db.close()


# ========== 厨房助手：后厨视图 ==========

def get_kitchen_orders():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT o.*, t.table_number
            FROM orders o
            JOIN tables_info t ON o.table_id=t.table_id
            WHERE o.status != '已结账'
            ORDER BY o.created_at ASC
        """)
        return cur.fetchall()
    finally:
        db.close()


def get_kitchen_items_by_dish():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT oi.detail_id, oi.item_id, oi.quantity, oi.status, oi.remark,
                   mi.name, mi.price,
                   o.order_id, t.table_number
            FROM order_items oi
            JOIN menu_items mi ON oi.item_id=mi.item_id
            JOIN orders o ON oi.order_id=o.order_id
            JOIN tables_info t ON o.table_id=t.table_id
            WHERE o.status != '已结账'
            ORDER BY mi.name, o.created_at ASC
        """)
        rows = cur.fetchall()
        dishes = {}
        for r in rows:
            key = r["item_id"]
            if key not in dishes:
                dishes[key] = {
                    "item_id": r["item_id"],
                    "name": r["name"],
                    "price": r["price"],
                    "total_pending": 0,
                    "items": [],
                }
            dishes[key]["items"].append({
                "detail_id": r["detail_id"],
                "order_id": r["order_id"],
                "table_number": r["table_number"],
                "quantity": r["quantity"],
                "remark": r["remark"],
                "status": r["status"],
            })
            if r["status"] in ("待制作", "制作中"):
                dishes[key]["total_pending"] += r["quantity"]
        result = list(dishes.values())
        result.sort(key=lambda d: d["total_pending"], reverse=True)
        return result
    finally:
        db.close()


def get_kitchen_dashboard_stats():
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT COUNT(DISTINCT order_id) FROM order_items WHERE status IN ('待制作','制作中')")
        pending_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM order_items WHERE status IN ('待制作','制作中')")
        pending_items = cur.fetchone()[0]
        cur.execute("SELECT COUNT(DISTINCT item_id) FROM order_items WHERE status IN ('待制作','制作中')")
        dishes_count = cur.fetchone()[0]
        cur.execute("SELECT item_id, name, stock FROM menu_items WHERE stock < 10 AND is_available=1 ORDER BY stock ASC LIMIT 5")
        alerts = [{"item_id": r["item_id"], "name": r["name"], "stock": r["stock"]} for r in cur.fetchall()]
        return {
            "total_pending_orders": pending_orders,
            "total_pending_items": pending_items,
            "dishes_count": dishes_count,
            "stock_alerts": alerts,
        }
    finally:
        db.close()


def get_order_items_by_status(order_id, status=None):
    db = get_db()
    try:
        cur = db.cursor()
        if status:
            cur.execute("""
                SELECT oi.*, mi.name as item_name
                FROM order_items oi
                JOIN menu_items mi ON oi.item_id=mi.item_id
                WHERE oi.order_id=? AND oi.status=?
                ORDER BY oi.detail_id
            """, (order_id, status))
        else:
            cur.execute("""
                SELECT oi.*, mi.name as item_name
                FROM order_items oi
                JOIN menu_items mi ON oi.item_id=mi.item_id
                WHERE oi.order_id=?
                ORDER BY oi.detail_id
            """, (order_id,))
        return cur.fetchall()
    finally:
        db.close()


# ========== 厨房助手：单品状态更新 ==========

def batch_update_item_status(detail_ids, new_status):
    db = get_db()
    try:
        cur = db.cursor()
        placeholders = ",".join("?" for _ in detail_ids)
        cur.execute(f"UPDATE order_items SET status=? WHERE detail_id IN ({placeholders})", (new_status, *detail_ids))
        db.commit()
        return cur.rowcount
    finally:
        db.close()


# ========== 厨房助手：退菜/损耗 ==========

def void_order_item(detail_id, reason):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT oi.*, mi.name as item_name
            FROM order_items oi
            JOIN menu_items mi ON oi.item_id=mi.item_id
            WHERE oi.detail_id=?
        """, (detail_id,))
        item = cur.fetchone()
        if not item:
            return {"ok": False, "message": "未找到该订单项"}
        cur.execute("UPDATE menu_items SET stock = stock + ? WHERE item_id=?", (item["quantity"], item["item_id"]))
        cur.execute(
            "INSERT INTO waste_log (order_id, item_id, item_name, quantity, reason) VALUES (?,?,?,?,?)",
            (item["order_id"], item["item_id"], item["item_name"], item["quantity"], reason),
        )
        cur.execute("DELETE FROM order_items WHERE detail_id=?", (detail_id,))
        db.commit()
        return {
            "ok": True,
            "message": f"已退菜：{item['item_name']} × {item['quantity']}，原因：{reason}",
            "item_name": item["item_name"],
            "quantity": item["quantity"],
        }
    except Exception as e:
        db.rollback()
        return {"ok": False, "message": f"退菜失败：{str(e)}"}
    finally:
        db.close()


def get_waste_log(limit=20):
    db = get_db()
    try:
        cur = db.cursor()
        cur.execute("SELECT * FROM waste_log ORDER BY created_at DESC LIMIT ?", (limit,))
        return cur.fetchall()
    finally:
        db.close()


def rush_order(order_id):
    """标记订单为加急"""
    db = get_db()
    db.execute("UPDATE orders SET is_rushed=1 WHERE order_id=?", (order_id,))
    db.commit()
    db.close()


def cancel_item_in_order(order_id, item_name, quantity):
    """按菜品名称退菜：将指定数量的某个菜品标记为'已取消'状态，回滚库存

    返回: {"ok": True/False, "message": "..."}
    """
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT oi.detail_id, oi.item_id, oi.quantity, oi.unit_price
        FROM order_items oi
        JOIN menu_items mi ON oi.item_id = mi.item_id
        WHERE oi.order_id=? AND mi.name=? AND oi.status='待制作'
        ORDER BY oi.detail_id
    """, (order_id, item_name))
    rows = cur.fetchall()

    if not rows:
        # 检查菜品是否存在但正在制作中
        cur.execute("""
            SELECT oi.status FROM order_items oi
            JOIN menu_items mi ON oi.item_id = mi.item_id
            WHERE oi.order_id=? AND mi.name=?
        """, (order_id, item_name))
        existing = cur.fetchone()
        db.close()
        if existing and existing["status"] in ("制作中", "待出餐", "已出餐"):
            return {"ok": False, "message": f"{item_name} 正在制作中，无法取消"}
        return {"ok": False, "message": f"订单中未找到菜品: {item_name}"}

    to_cancel = min(quantity, sum(r["quantity"] for r in rows))
    if to_cancel < quantity:
        db.close()
        return {"ok": False, "message": f"订单中'{item_name}'只有 {to_cancel} 份可取消"}

    cancelled = 0
    for row in rows:
        if cancelled >= quantity:
            break
        cancel_qty = min(row["quantity"], quantity - cancelled)
        detail_id = row["detail_id"]
        db.execute("UPDATE order_items SET status='已取消' WHERE detail_id=?", (detail_id,))
        db.execute("UPDATE menu_items SET stock = stock + ? WHERE item_id=?", (cancel_qty, row["item_id"]))
        cur.execute("SELECT name FROM menu_items WHERE item_id=?", (row["item_id"],))
        item_name_str = cur.fetchone()["name"]
        db.execute(
            "INSERT INTO waste_log (order_id, item_id, item_name, quantity, reason) VALUES (?,?,?,?,?)",
            (order_id, row["item_id"], item_name_str, cancel_qty, "顾客取消"),
        )
        cancelled += cancel_qty

    # 重新计算订单总金额，追加取消备注
    db.execute("""
        UPDATE orders SET total_amount = (SELECT COALESCE(SUM(subtotal),0) FROM order_items WHERE order_id=? AND status!='已取消'),
        note = CASE WHEN note = '' THEN ? ELSE note || '；' || ? END
        WHERE order_id=?
    """, (order_id, f"【已取消】{item_name}x{cancelled}", f"【已取消】{item_name}x{cancelled}", order_id))
    db.commit()
    db.close()
    return {"ok": True, "message": f"已取消 {item_name} x {cancelled}"}


def update_stock(item_id, stock_qty):
    """设置某个菜品的库存（覆盖式）"""
    db = get_db()
    db.execute("UPDATE menu_items SET stock=? WHERE item_id=?", (stock_qty, item_id))
    db.commit()
    db.close()


def check_order_stock(items):
    """检查下单时的库存是否充足

    参数 items: [{"item_id": 1, "quantity": 2}, ...]
    返回: (ok: bool, 消息: str)
    """
    db = get_db()
    cur = db.cursor()
    for item in items:
        cur.execute("SELECT name, stock FROM menu_items WHERE item_id=?", (item["item_id"],))
        menu = cur.fetchone()
        if menu:
            if menu["stock"] < item["quantity"]:
                db.close()
                return False, f"{menu['name']} 库存不足（仅剩 {menu['stock']} 份）"
    db.close()
    return True, ""


def deduct_order_stock(items):
    """下单成功时扣减库存

    参数 items: [{"item_id": 1, "quantity": 2}, ...]
    """
    db = get_db()
    for item in items:
        db.execute("UPDATE menu_items SET stock = stock - ? WHERE item_id=?",
                   (item["quantity"], item["item_id"]))
    db.commit()
    db.close()


def save_draft(draft_key, table_id, items, note, total):
    db = get_db()
    db.execute("INSERT OR REPLACE INTO order_drafts (draft_key, table_id, items, note, total) VALUES (?,?,?,?,?)",
               (draft_key, table_id, json.dumps(items), note, total))
    db.commit()
    db.close()


def get_draft(draft_key):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM order_drafts WHERE draft_key=?", (draft_key,))
    row = cur.fetchone()
    if row:
        row = dict(row)
        row["items"] = json.loads(row["items"])
    db.close()
    return row


def delete_draft(draft_key):
    db = get_db()
    db.execute("DELETE FROM order_drafts WHERE draft_key=?", (draft_key,))
    db.commit()
    db.close()


def draft_exists(draft_key):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT 1 FROM order_drafts WHERE draft_key=?", (draft_key,))
    exists = cur.fetchone() is not None
    db.close()
    return exists
