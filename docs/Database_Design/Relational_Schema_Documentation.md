# StockMaster – Relational Schema Documentation

## 1. Introduction

The StockMaster database is designed using the relational database model. It consists of 15 tables connected through primary key and foreign key relationships.

The database manages users, roles, products, categories, suppliers, customers, warehouses, inventory, purchase orders, sales, stock movements and warehouse transfers.

Database Name: stockmaster_db

## 2. Relational Schema Notation

The following notation is used:

- PK: Primary Key
- FK: Foreign Key
- UK: Unique Key
- INT: Integer
- VARCHAR: Variable-length character data
- DECIMAL: Numeric values with decimal precision
- DATE: Date value
- DATETIME: Date and time value
- BOOLEAN: True or false value

## 3. Relational Schema of All Tables

### 3.1 ROLES

| Attribute | Key |
|---|---|
| role_id | PK |
| role_name | UK |
| description | |

Purpose: Stores the different roles available in the system, such as Admin, Manager, Staff and Analyst.

### 3.2 USERS

| Attribute | Key |
|---|---|
| user_id | PK |
| role_id | FK → roles.role_id |
| full_name | |
| email | UK |
| password_hash | |
| created_at | |
| is_active | |

Purpose: Stores registered system users and their assigned roles.

### 3.3 WAREHOUSES

| Attribute | Key |
|---|---|
| warehouse_id | PK |
| warehouse_name | |
| location | |
| contact_number | |
| created_at | |

Purpose: Stores warehouse information and locations.

### 3.4 SUPPLIERS

| Attribute | Key |
|---|---|
| supplier_id | PK |
| supplier_name | |
| contact_person | |
| email | |
| phone | |
| address | |

Purpose: Stores supplier information for purchase management.

### 3.5 CATEGORIES

| Attribute | Key |
|---|---|
| category_id | PK |
| category_name | UK |
| description | |

Purpose: Organizes products into categories.

### 3.6 PRODUCTS

| Attribute | Key |
|---|---|
| product_id | PK |
| category_id | FK → categories.category_id |
| sku | UK |
| product_name | |
| description | |
| unit_price | |
| reorder_level | |
| created_at | |

Purpose: Stores product details, pricing and reorder information.

### 3.7 CUSTOMERS

| Attribute | Key |
|---|---|
| customer_id | PK |
| customer_name | |
| email | |
| phone | |
| address | |
| customer_type | |

Purpose: Stores customer information for sales transactions.

### 3.8 STOCK

| Attribute | Key |
|---|---|
| stock_id | PK |
| product_id | FK → products.product_id |
| warehouse_id | FK → warehouses.warehouse_id |
| quantity | |
| updated_at | |

Purpose: Maintains the quantity of each product available in each warehouse.

Business rule: A product should have only one stock-balance record per warehouse. The product_id and warehouse_id combination should therefore be unique.

### 3.9 PURCHASE_ORDERS

| Attribute | Key |
|---|---|
| purchase_order_id | PK |
| supplier_id | FK → suppliers.supplier_id |
| warehouse_id | FK → warehouses.warehouse_id |
| created_by | FK → users.user_id |
| order_date | |
| expected_date | |
| status | |

Purpose: Stores purchase order information.

### 3.10 PURCHASE_ORDER_ITEMS

| Attribute | Key |
|---|---|
| purchase_item_id | PK |
| purchase_order_id | FK → purchase_orders.purchase_order_id |
| product_id | FK → products.product_id |
| quantity | |
| unit_cost | |

Purpose: Stores individual products and quantities included in purchase orders.

### 3.11 SALES

| Attribute | Key |
|---|---|
| sale_id | PK |
| customer_id | FK → customers.customer_id |
| warehouse_id | FK → warehouses.warehouse_id |
| sold_by | FK → users.user_id |
| sale_date | |
| status | |

Purpose: Stores sales transaction information.

### 3.12 SALE_ITEMS

| Attribute | Key |
|---|---|
| sale_item_id | PK |
| sale_id | FK → sales.sale_id |
| product_id | FK → products.product_id |
| quantity | |
| unit_price | |

Purpose: Stores individual products sold in each sales transaction.

### 3.13 STOCK_MOVEMENTS

| Attribute | Key |
|---|---|
| movement_id | PK |
| product_id | FK → products.product_id |
| warehouse_id | FK → warehouses.warehouse_id |
| movement_type | |
| quantity | |
| reference_note | |
| performed_by | FK → users.user_id |
| movement_date | |

Purpose: Maintains an audit trail of stock changes, including stock-in, stock-out, adjustments and warehouse transfers.

### 3.14 WAREHOUSE_TRANSFERS

| Attribute | Key |
|---|---|
| transfer_id | PK |
| source_warehouse_id | FK → warehouses.warehouse_id |
| destination_warehouse_id | FK → warehouses.warehouse_id |
| transferred_by | FK → users.user_id |
| transfer_date | |
| status | |

Purpose: Stores information about stock transfers between warehouses.

### 3.15 TRANSFER_ITEMS

| Attribute | Key |
|---|---|
| transfer_item_id | PK |
| transfer_id | FK → warehouse_transfers.transfer_id |
| product_id | FK → products.product_id |
| quantity | |

Purpose: Stores individual products and quantities included in warehouse transfers.

## 4. Primary Key Summary

| Table | Primary Key |
|---|---|
| roles | role_id |
| users | user_id |
| warehouses | warehouse_id |
| suppliers | supplier_id |
| categories | category_id |
| products | product_id |
| customers | customer_id |
| stock | stock_id |
| purchase_orders | purchase_order_id |
| purchase_order_items | purchase_item_id |
| sales | sale_id |
| sale_items | sale_item_id |
| stock_movements | movement_id |
| warehouse_transfers | transfer_id |
| transfer_items | transfer_item_id |

## 5. Foreign Key Relationships

| Child Table | Foreign Key | Referenced Table |
|---|---|---|
| users | role_id | roles.role_id |
| products | category_id | categories.category_id |
| stock | product_id | products.product_id |
| stock | warehouse_id | warehouses.warehouse_id |
| purchase_orders | supplier_id | suppliers.supplier_id |
| purchase_orders | warehouse_id | warehouses.warehouse_id |
| purchase_orders | created_by | users.user_id |
| purchase_order_items | purchase_order_id | purchase_orders.purchase_order_id |
| purchase_order_items | product_id | products.product_id |
| sales | customer_id | customers.customer_id |
| sales | warehouse_id | warehouses.warehouse_id |
| sales | sold_by | users.user_id |
| sale_items | sale_id | sales.sale_id |
| sale_items | product_id | products.product_id |
| stock_movements | product_id | products.product_id |
| stock_movements | warehouse_id | warehouses.warehouse_id |
| stock_movements | performed_by | users.user_id |
| warehouse_transfers | source_warehouse_id | warehouses.warehouse_id |
| warehouse_transfers | destination_warehouse_id | warehouses.warehouse_id |
| warehouse_transfers | transferred_by | users.user_id |
| transfer_items | transfer_id | warehouse_transfers.transfer_id |
| transfer_items | product_id | products.product_id |

Total documented foreign key relationships: 22.

## 6. Relationship Cardinality

| Relationship | Cardinality |
|---|---|
| Roles → Users | One-to-Many |
| Categories → Products | One-to-Many |
| Products → Stock | One-to-Many |
| Warehouses → Stock | One-to-Many |
| Suppliers → Purchase Orders | One-to-Many |
| Warehouses → Purchase Orders | One-to-Many |
| Purchase Orders → Purchase Order Items | One-to-Many |
| Products → Purchase Order Items | One-to-Many |
| Customers → Sales | One-to-Many |
| Warehouses → Sales | One-to-Many |
| Sales → Sale Items | One-to-Many |
| Products → Sale Items | One-to-Many |
| Products → Stock Movements | One-to-Many |
| Warehouses → Stock Movements | One-to-Many |
| Warehouses → Warehouse Transfers | One-to-Many |
| Warehouse Transfers → Transfer Items | One-to-Many |
| Products → Transfer Items | One-to-Many |

Note: Users also participate in purchase orders, sales, stock movements and warehouse transfers through their respective foreign keys.

## 7. Integrity Constraints

The database uses the following integrity mechanisms:

1. Entity Integrity: Primary keys uniquely identify table records.
2. Referential Integrity: Foreign keys connect related tables.
3. Domain Integrity: Column data types restrict the kind of values stored.
4. Unique Constraints: Important identifiers such as email, SKU, role name and category name are protected against duplicates.
5. Transaction Integrity: Stock operations use database transactions to prevent incomplete updates.
6. Business Rules: Stock quantities must not become negative during supported stock operations.

## 8. Conclusion

The StockMaster relational schema organizes the inventory management system into 15 interconnected tables.

Primary keys provide unique identification, while foreign keys maintain relationships and referential integrity.

The schema supports product management, warehouse inventory, purchasing, sales, stock movement tracking and warehouse transfers. It provides the database foundation for the StockMaster application and its reporting features.
