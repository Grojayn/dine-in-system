import sqlite3
import secrets
from flask import Flask, session as flask_session, request

_db_initialized = False


def _init_schema(db):
    """建表 + 迁移（启动时执行一次）"""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS tables_info (
            table_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number TEXT NOT NULL UNIQUE,
            capacity INTEGER NOT NULL DEFAULT 4,
            status TEXT NOT NULL DEFAULT '空闲' CHECK(status IN ('空闲','已占用','待结账'))
        );
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sort_order INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS menu_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT DEFAULT '',
            image TEXT DEFAULT '',
            is_available INTEGER NOT NULL DEFAULT 1,
            is_recommended INTEGER NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 50,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,
            order_number TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT '已下单' CHECK(status IN ('已下单','制作中','已上菜','已结账')),
            total_amount REAL NOT NULL DEFAULT 0,
            is_rushed INTEGER NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
            paid_at DATETIME DEFAULT NULL,
            FOREIGN KEY (table_id) REFERENCES tables_info(table_id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            status TEXT NOT NULL DEFAULT '待制作' CHECK(status IN ('待制作','制作中','待出餐','已出餐','已取消')),
            remark TEXT DEFAULT '',
            FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        );
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            table_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            round INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS waste_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            item_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reason TEXT NOT NULL,
            created_at DATETIME DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
        CREATE TABLE IF NOT EXISTS order_drafts (
            draft_key TEXT PRIMARY KEY,
            table_id INTEGER NOT NULL,
            items TEXT NOT NULL,
            note TEXT DEFAULT '',
            total REAL NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT (datetime('now','localtime'))
        );
    """)
    db.commit()

    # === 存量数据库迁移 ===
    cur = db.cursor()

    # stock 列
    cur.execute("PRAGMA table_info(menu_items)")
    if 'stock' not in [row[1] for row in cur.fetchall()]:
        cur.execute("ALTER TABLE menu_items ADD COLUMN stock INTEGER NOT NULL DEFAULT 0")
        cur.execute("UPDATE menu_items SET stock = 50 WHERE stock = 0")

    # is_rushed 列
    cur.execute("PRAGMA table_info(orders)")
    if 'is_rushed' not in [row[1] for row in cur.fetchall()]:
        cur.execute("ALTER TABLE orders ADD COLUMN is_rushed INTEGER NOT NULL DEFAULT 0")

    # order_items 状态扩展（针对存量库）
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='order_items'")
    ddl = (cur.fetchone() or ["", ""])[0]
    if "'待出餐'" not in ddl:
        cur.executescript("""
            PRAGMA foreign_keys=OFF;
            CREATE TABLE order_items_new (
                detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1, unit_price REAL NOT NULL, subtotal REAL NOT NULL,
                status TEXT NOT NULL DEFAULT '待制作' CHECK(status IN ('待制作','制作中','待出餐','已出餐','已取消')),
                remark TEXT DEFAULT '',
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
                FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
            );
            INSERT INTO order_items_new SELECT * FROM order_items;
            DROP TABLE order_items;
            ALTER TABLE order_items_new RENAME TO order_items;
            PRAGMA foreign_keys=ON;
        """)

    db.commit()


def _insert_sample_data(db):
    cur = db.cursor()
    if cur.execute("SELECT COUNT(*) FROM tables_info").fetchone()[0] > 0:
        return
    tables = [('A01',4),('A02',4),('A03',6),('A04',2),('A05',4),('A06',6),('A07',8),('A08',4),('B01',4),('B02',6)]
    cur.executemany("INSERT INTO tables_info (table_number, capacity) VALUES (?,?)", tables)
    cats = [('招牌热菜',1),('精致凉菜',2),('汤羹煲类',3),('主食面点',4),('酒水饮品',5)]
    cur.executemany("INSERT INTO categories (name, sort_order) VALUES (?,?)", cats)
    items = [
        (1,'宫保鸡丁',32,'精选鸡腿肉，配花生米干辣椒爆炒，麻辣鲜香',1,50),(1,'红烧狮子头',38,'手工剁制大肉丸，慢火炖煮，软糯入味',1,50),
        (1,'水煮鱼片',48,'新鲜草鱼片，麻辣汤底，嫩滑爽口',0,50),(1,'糖醋里脊',28,'猪里脊肉挂糊炸制，酸甜可口',1,50),
        (1,'干煸四季豆',22,'四季豆煸至微焦，配蒜末辣椒同炒',0,50),(1,'鱼香肉丝',26,'经典川味，酸辣甜兼备',0,50),
        (2,'凉拌黄瓜',12,'清脆爽口，蒜泥调味',0,50),(2,'口水鸡',28,'白斩鸡淋红油，麻辣鲜香',1,50),
        (2,'皮蛋豆腐',15,'嫩豆腐配松花蛋，淋香油酱油',0,50),(2,'夫妻肺片',32,'牛腱牛肚薄片，红油拌制',1,50),
        (3,'番茄蛋花汤',16,'经典家常汤品',0,50),(3,'酸辣汤',18,'酸辣开胃，料足味浓',0,50),
        (3,'排骨玉米汤',35,'慢炖排骨配甜玉米，浓郁鲜甜',1,50),(4,'蛋炒饭',15,'粒粒分明，简单美味',0,50),
        (4,'手工水饺(猪肉白菜)',22,'现包现煮，12只/份',1,50),(4,'阳春面',12,'清汤细面，葱花点缀',0,50),
        (4,'葱油饼',8,'外酥里软，葱香四溢',0,50),(5,'可乐',5,'330ml罐装',0,50),
        (5,'王老吉',6,'310ml罐装',0,50),(5,'青岛啤酒',10,'500ml瓶装',0,50),(5,'酸梅汤',8,'自制冰镇酸梅汤',1,50)
    ]
    cur.executemany("INSERT INTO menu_items (category_id, name, price, description, is_recommended, stock) VALUES (?,?,?,?,?,?)", items)
    cur.execute("INSERT INTO admins (username, password) VALUES (?,?)", ('admin', 'scrypt:32768:8:1$Yvg57rjF21lwPdxE$8f369fe7e9472fce9da684d9686f1f1bd9bc801cd539ea4615057a68baffa6927b64bf18a7be8c8bad47d62278666a882bd34a84be9633b3730df538b4e09bd6'))
    db.commit()


def ensure_db():
    """应用启动时执行一次：建表 + 迁移 + 初始数据"""
    global _db_initialized
    if _db_initialized:
        return
    from config import DB_PATH
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON")
    _init_schema(db)
    _insert_sample_data(db)
    db.close()
    _db_initialized = True


def get_db():
    """每次请求的数据库连接，不复用连接池，但不再跑迁移"""
    from config import DB_PATH
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def create_app():
    app = Flask(__name__)
    app.config.from_object("config")
    app.secret_key = app.config["SECRET_KEY"]

    # 启动时初始化数据库
    ensure_db()

    # CSRF 防护（仅保护关键操作路径）
    CSRF_PATHS = ('/order', '/pay', '/reset', '/select-table',
                  '/admin/orders/', '/admin/categories', '/admin/menu',
                  '/admin/tables', '/admin/logout')

    @app.before_request
    def csrf_guard():
        if '_csrf_token' not in flask_session:
            flask_session['_csrf_token'] = secrets.token_hex(16)
        if request.method == "POST" and request.path.startswith(CSRF_PATHS):
            token = request.form.get("csrf_token", "")
            if not token or token != flask_session.get('_csrf_token'):
                return "CSRF验证失败，请刷新页面重试", 403

    @app.context_processor
    def inject_csrf():
        return {'csrf_token': flask_session.get('_csrf_token', '')}

    # WSGI 中间件：读取 Nginx 的 X-Script-Name 头，使 url_for() 自动添加前缀
    class _ReverseProxied:
        def __init__(self, app):
            self.app = app
        def __call__(self, environ, start_response):
            script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
            if script_name:
                environ['SCRIPT_NAME'] = script_name
                path = environ['PATH_INFO']
                if path.startswith(script_name):
                    environ['PATH_INFO'] = path[len(script_name):]
            return self.app(environ, start_response)

    app.wsgi_app = _ReverseProxied(app.wsgi_app)

    from app.routes import customer, admin, assistant, kitchen
    app.register_blueprint(customer.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(assistant.bp)
    app.register_blueprint(kitchen.bp)
    return app
