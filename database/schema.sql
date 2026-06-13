-- ============================================
-- 顾客堂食点餐系统 - 数据库建表脚本
-- 数据库名称: dine_in_system
-- ============================================

CREATE DATABASE IF NOT EXISTS dine_in_system DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dine_in_system;

-- 删除旧表（按外键依赖顺序）
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS menu_items;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS tables_info;
DROP TABLE IF EXISTS admins;

-- 1. 桌位表
CREATE TABLE tables_info (
    table_id INT AUTO_INCREMENT PRIMARY KEY,
    table_number VARCHAR(10) NOT NULL UNIQUE,
    capacity INT NOT NULL DEFAULT 4,
    status ENUM('空闲', '已占用', '待结账') NOT NULL DEFAULT '空闲'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 菜品分类表
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    sort_order INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. 菜品表
CREATE TABLE menu_items (
    item_id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description VARCHAR(500) DEFAULT '',
    image VARCHAR(255) DEFAULT '',
    is_available TINYINT NOT NULL DEFAULT 1,
    is_recommended TINYINT NOT NULL DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 订单表
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    table_id INT NOT NULL,
    order_number VARCHAR(20) NOT NULL UNIQUE,
    status ENUM('已下单', '制作中', '已上菜', '已结账') NOT NULL DEFAULT '已下单',
    total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    note VARCHAR(500) DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME DEFAULT NULL,
    FOREIGN KEY (table_id) REFERENCES tables_info(table_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 订单明细表
CREATE TABLE order_items (
    detail_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    status ENUM('待制作', '制作中', '已完成') NOT NULL DEFAULT '待制作',
    remark VARCHAR(500) DEFAULT '',
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (item_id) REFERENCES menu_items(item_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 管理员表
CREATE TABLE admins (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
