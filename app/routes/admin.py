from flask import Blueprint, render_template, request, redirect, url_for, session
from app import models
from functools import wraps

bp = Blueprint("admin", __name__, url_prefix="/admin")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_logged_in" not in session:
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if models.verify_admin(username, password):
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        return render_template("admin/login.html", error="用户名或密码错误")
    return render_template("admin/login.html")

@bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))

@bp.route("/dashboard")
@login_required
def dashboard():
    orders = models.get_all_orders()
    tables = models.get_tables()
    return render_template("admin/dashboard.html", orders=orders, tables=tables)

@bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            models.add_category(request.form["name"], int(request.form.get("sort_order", 0)))
        elif action == "update":
            models.update_category(int(request.form["category_id"]), request.form["name"], int(request.form.get("sort_order", 0)))
        elif action == "delete":
            models.delete_category(int(request.form["category_id"]))
    cats = models.get_categories()
    return render_template("admin/categories.html", categories=cats)

@bp.route("/menu", methods=["GET", "POST"])
@login_required
def menu_items():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            models.add_menu_item(int(request.form["category_id"]), request.form["name"],
                                float(request.form["price"]), request.form.get("description", ""),
                                int(request.form.get("is_recommended", 0)))
        elif action == "update":
            models.update_menu_item(int(request.form["item_id"]), int(request.form["category_id"]),
                                   request.form["name"], float(request.form["price"]),
                                   request.form.get("description", ""),
                                   int(request.form.get("is_available", 1)),
                                   int(request.form.get("is_recommended", 0)),
                                   int(request.form.get("stock", 0)))
        elif action == "delete":
            models.delete_menu_item(int(request.form["item_id"]))
    items = models.get_all_menu_items()
    cats = models.get_categories()
    return render_template("admin/menu_items.html", menu_items=items, categories=cats)

@bp.route("/tables", methods=["GET", "POST"])
@login_required
def tables():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            models.add_table(request.form["table_number"], int(request.form.get("capacity", 4)))
        elif action == "update":
            models.update_table_info(int(request.form["table_id"]), request.form["table_number"], int(request.form.get("capacity", 4)))
        elif action == "delete":
            models.delete_table(int(request.form["table_id"]))
    tables = models.get_tables()
    return render_template("admin/tables.html", tables=tables)

@bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    order = models.get_order_info(order_id)
    items = models.get_order_detail(order_id)
    return render_template("admin/order_detail.html", order=order, items=items)

@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
def update_order_status(order_id):
    status = request.form.get("status")
    models.update_order_status(order_id, status)
    if status in ("制作中", "已上菜"):
        order = models.get_order_info(order_id)
        if order:
            from app.routes.kitchen import push_notification
            push_notification("item_updated", {
                "table_id": order["table_id"],
                "status": status,
            })
    return redirect(url_for("admin.dashboard"))

@bp.route("/orders/item/<int:detail_id>/status", methods=["POST"])
@login_required
def update_item_status(detail_id):
    status = request.form.get("status")
    models.update_order_item_status(detail_id, status)
    return redirect(request.referrer or url_for("admin.dashboard"))
