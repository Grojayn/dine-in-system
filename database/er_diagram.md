# 顾客堂食点餐系统 - 数据库 ER 图

> 本文档展示 dine_in_system 数据库的实体关系图，包含 6 张核心表及其关联关系。

```mermaid
erDiagram
    tables_info {
        int table_id PK "主键，自增"
        varchar table_number UK "桌号，唯一"
        int capacity "座位数"
        enum status "状态：空闲、已占用、待结账"
    }

    categories {
        int category_id PK "主键，自增"
        varchar name "分类名称"
        int sort_order "排序权重"
    }

    menu_items {
        int item_id PK "主键，自增"
        int category_id FK "所属分类"
        varchar name "菜品名称"
        decimal price "单价"
        varchar description "描述"
        varchar image "图片路径"
        tinyint is_available "是否可售"
        tinyint is_recommended "是否推荐"
    }

    orders {
        int order_id PK "主键，自增"
        int table_id FK "所属桌位"
        varchar order_number UK "订单编号，唯一"
        enum status "状态：已下单、制作中、已上菜、已结账"
        decimal total_amount "订单总金额"
        varchar note "备注"
        datetime created_at "创建时间"
        datetime paid_at "结账时间"
    }

    order_items {
        int detail_id PK "主键，自增"
        int order_id FK "所属订单"
        int item_id FK "关联菜品"
        int quantity "数量"
        decimal unit_price "下单时单价"
        decimal subtotal "小计"
        enum status "状态：待制作、制作中、已完成"
        varchar remark "口味备注"
    }

    admins {
        int admin_id PK "主键，自增"
        varchar username UK "用户名，唯一"
        varchar password "登录密码（加密存储）"
    }

    %% ==================== 关系定义 ====================

    categories ||--o{ menu_items : "一对多：一个分类下包含多个菜品"
    menu_items ||--o{ order_items : "一对多：一个菜品可出现在多条订单明细中"
    tables_info ||--o{ orders : "一对多：一张桌位可产生多条订单"
    orders ||--o{ order_items : "一对多：一笔订单包含多条菜品明细"
```

## 表关系汇总

| 主表 | 从表 | 关系类型 | 外键 | 说明 |
|------|------|----------|------|------|
| categories | menu_items | 一对多 | category_id | 一个分类下有多个菜品 |
| menu_items | order_items | 一对多 | item_id | 一个菜品可被多次点单 |
| tables_info | orders | 一对多 | table_id | 一张桌位可有多笔订单 |
| orders | order_items | 一对多 | order_id | 一笔订单可有多个菜品明细 |

## 状态流转说明

- **桌位状态**: `空闲` -> `已占用`（顾客入座） -> `待结账`（请求买单） -> `空闲`（结账完成）
- **订单状态**: `已下单` -> `制作中` -> `已上菜` -> `已结账`
- **订单明细状态**: `待制作` -> `制作中` -> `已完成`
