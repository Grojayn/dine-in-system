from flask import Blueprint, render_template, request, redirect, url_for, session
from app import models

bp = Blueprint("customer", __name__, url_prefix="")

@bp.route("/")
def index():
    return render_template("customer/index.html")

@bp.route("/select-table", methods=["POST"])
def select_table():
    table_number = request.form.get("table_number", "").strip().upper()
    table = models.get_table_by_number(table_number)
    if not table:
        return render_template("customer/index.html", error="桌号不存在，请重新输入")
    session["table_id"] = table["table_id"]
    session["table_number"] = table["table_number"]
    if table["status"] == "已占用":
        return redirect(url_for("customer.order_status"))
    models.occupy_table(table["table_id"])
    return redirect(url_for("customer.menu"))

@bp.route("/menu")
def menu():
    if "table_id" not in session:
        return redirect(url_for("customer.index"))
    categories = models.get_categories()
    menu_items = models.get_menu_by_category()
    return render_template("customer/menu.html", categories=categories, menu_items=menu_items, table_number=session.get("table_number"))

@bp.route("/order", methods=["POST"])
def order():
    if "table_id" not in session:
        return redirect(url_for("customer.index"))
    item_ids = request.form.getlist("item_id[]")
    quantities = request.form.getlist("quantity[]")
    remarks = request.form.getlist("remark[]")
    note = request.form.get("note", "")
    items = []
    for i in range(len(item_ids)):
        qty = int(quantities[i])
        if qty > 0:
            items.append({"item_id": int(item_ids[i]), "quantity": qty, "remark": remarks[i] if i < len(remarks) else ""})
    if not items:
        return redirect(url_for("customer.menu"))
    ok, msg = models.check_order_stock(items)
    if not ok:
        return msg, 400
    order_id, order_number = models.create_order(session["table_id"], items, note)
    models.deduct_order_stock(items)
    session["order_id"] = order_id
    session["order_number"] = order_number
    # 通知小味：顾客已自主下单
    from app.assistant.memory import add_message
    from app import get_db
    sid = session.get("assistant_sid")
    if sid:
        db = get_db()
        cur = db.cursor()
        ids = [str(item["item_id"]) for item in items]
        cur.execute(f"SELECT item_id, name FROM menu_items WHERE item_id IN ({','.join(ids)})")
        name_map = {r["item_id"]: r["name"] for r in cur.fetchall()}
        names = [f"{name_map[i['item_id']]}×{i['quantity']}" for i in items if i['item_id'] in name_map]
        db.close()
        msg = f"顾客已自主下单：{'、'.join(names)}。订单号：{order_number}"
        add_message(sid, session["table_id"], "assistant", msg)
    return redirect(url_for("customer.order_status"))

@bp.route("/order-status")
def order_status():
    if "table_id" not in session:
        return redirect(url_for("customer.index"))
    table_id = session["table_id"]
    orders = models.get_table_orders(table_id)
    if not orders:
        session.pop("order_id", None)
        session.pop("order_number", None)
        return render_template("customer/order_status.html", orders=None, table_number=session.get("table_number"))
    # 取出所有订单的详情
    order_list = []
    for o in orders:
        items = models.get_order_detail(o["order_id"])
        order_list.append({"order": o, "items": items})
    return render_template("customer/order_status.html", orders=order_list, table_number=session.get("table_number"))

@bp.route("/pay", methods=["POST"])
def pay():
    if "table_id" not in session:
        return redirect(url_for("customer.index"))
    table_id = session["table_id"]
    tn = session.get("table_number", "")
    models.pay_all_orders(table_id)
    session.clear()
    return render_template("customer/pay_success.html", table_number=tn)

@bp.route("/reset")
def reset():
    session.clear()
    return redirect(url_for("customer.index"))
