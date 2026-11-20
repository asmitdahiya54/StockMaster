# STOCKMASTER
# SQL IMPLEMENTATION AND QUERY DOCUMENTATION

Database: stockmaster_db
DBMS: MySQL 8+
Project: Smart Inventory and Warehouse Management System

============================================================
1. INTRODUCTION
============================================================

This document describes the SQL implementation of StockMaster.
The database uses MySQL and contains 15 relational tables.

The SQL implementation covers:
- Data Definition Language (DDL)
- Data Manipulation Language (DML)
- Data Control Language (DCL)
- Transaction Control Language (TCL)
- Joins
- Nested and correlated subqueries
- Set operations
- Views
- Indexing
- Common Table Expressions (CTEs)
- Window functions

============================================================
2. DATA DEFINITION LANGUAGE (DDL)
============================================================

DDL commands define and modify database structures.

Commands practised:

CREATE:
Creates a new database object.

Example:
CREATE TABLE ddl_practice (
    id INT PRIMARY KEY,
    test_name VARCHAR(100)
);

ALTER:
Modifies an existing table.

Example:
ALTER TABLE customers
ADD COLUMN customer_type VARCHAR(30);

TRUNCATE:
Removes all records from a table while retaining its structure.

Example:
TRUNCATE TABLE ddl_practice;

DROP:
Deletes a database object.

Example:
DROP TABLE ddl_practice;

Testing:
A temporary ddl_practice table was created, modified, truncated
and dropped successfully.

============================================================
3. DATA MANIPULATION LANGUAGE (DML)
============================================================

DML commands manipulate records stored in database tables.

INSERT:
Adds a new record.

Example:
INSERT INTO categories (category_name, description)
VALUES ('Accessories', 'Computer accessories');

SELECT:
Retrieves records.

Example:
SELECT * FROM products;

UPDATE:
Modifies existing records.

Example:
UPDATE products
SET unit_price = 1250
WHERE product_id = 1;

DELETE:
Removes selected records.

Example:
DELETE FROM categories
WHERE category_id = 10;

Testing:
INSERT, SELECT, UPDATE and DELETE operations were practised
on the StockMaster database.

============================================================
4. DATA CONTROL LANGUAGE (DCL)
============================================================

DCL manages database permissions and access.

A separate application database account named stockmaster_app
was created for the Flask backend.

Example:

GRANT SELECT, INSERT, UPDATE, DELETE
ON stockmaster_db.*
TO 'stockmaster_app'@'localhost';

Testing:
The application account was granted the required permissions.
Database access was tested successfully.

============================================================
5. TRANSACTION CONTROL LANGUAGE (TCL)
============================================================

TCL manages database transactions.

COMMIT:
Permanently saves transaction changes.

ROLLBACK:
Reverses uncommitted transaction changes.

Example:

START TRANSACTION;

UPDATE stock
SET quantity = quantity + 5
WHERE product_id = 1 AND warehouse_id = 1;

ROLLBACK;

A separate transaction was also committed successfully.

Stock operations in the application use transactions to prevent
incomplete inventory updates.

============================================================
6. SQL JOINS
============================================================

Joins combine related records from multiple tables.

6.1 INNER JOIN

Displays matching products and categories.

SELECT
    p.product_name,
    c.category_name
FROM products p
INNER JOIN categories c
ON p.category_id = c.category_id;

6.2 LEFT JOIN

Displays all customers, including customers without sales.

SELECT
    c.customer_name,
    s.sale_id
FROM customers c
LEFT JOIN sales s
ON c.customer_id = s.customer_id;

6.3 RIGHT JOIN

Displays all sales and their matching customer information.

SELECT
    c.customer_name,
    s.sale_id
FROM sales s
RIGHT JOIN customers c
ON s.customer_id = c.customer_id;

6.4 SELF JOIN

Compares customers with other customers having the same address.

SELECT
    c1.customer_name AS Customer1,
    c2.customer_name AS Customer2,
    c1.address
FROM customers c1
JOIN customers c2
ON c1.address = c2.address
AND c1.customer_id < c2.customer_id;

Testing:
INNER JOIN, LEFT JOIN, RIGHT JOIN and SELF JOIN were executed.

The SELF JOIN returned no matching records for the existing
customer addresses. This is a valid result.

============================================================
7. NESTED SUBQUERIES
============================================================

A nested subquery is a query written inside another SQL query.

Example: Find products priced above the average product price.

SELECT
    product_name,
    unit_price
FROM products
WHERE unit_price > (
    SELECT AVG(unit_price)
    FROM products
);

The average product price during testing was approximately
1882.47.

Products above that average included:
- LED Monitor 24 Inch
- External SSD 1TB
- Mechanical Keyboard
- WiFi Router

============================================================
8. CORRELATED SUBQUERIES
============================================================

A correlated subquery references columns from the outer query.

Example: Find products having low stock in at least one warehouse.

SELECT
    p.product_id,
    p.product_name
FROM products p
WHERE EXISTS (
    SELECT 1
    FROM stock st
    WHERE st.product_id = p.product_id
      AND st.quantity <= p.reorder_level
);

Testing:
The correlated EXISTS query was executed to identify products
with stock at or below their reorder levels.

============================================================
9. SET OPERATIONS
============================================================

Set operations combine results from multiple SELECT statements.

9.1 UNION

Combines results and removes duplicate rows.

SELECT product_id
FROM stock
WHERE warehouse_id = 1

UNION

SELECT product_id
FROM stock
WHERE warehouse_id = 2;

9.2 INTERSECT

Returns records present in both result sets.

SELECT product_id
FROM stock
WHERE warehouse_id = 1

INTERSECT

SELECT product_id
FROM stock
WHERE warehouse_id = 2;

9.3 EXCEPT

Returns records present in the first result but not the second.

SELECT product_id
FROM stock
WHERE warehouse_id = 1

EXCEPT

SELECT product_id
FROM stock
WHERE warehouse_id = 2;

Testing:
UNION, INTERSECT and EXCEPT were executed successfully
using MySQL 8.0.

============================================================
10. VIEWS
============================================================

Views are virtual tables based on SQL queries.

StockMaster contains two database views.

10.1 vw_purchase_order_summary

Purpose:
Displays purchase order information along with supplier,
warehouse, user, item count, total quantity and purchase value.

Verification:

SELECT * FROM vw_purchase_order_summary;

10.2 vw_low_stock_alert

Purpose:
Displays products whose warehouse stock is at or below
their reorder levels.

Verification:

SELECT * FROM vw_low_stock_alert;

Testing:
Both views were confirmed in INFORMATION_SCHEMA and
SHOW FULL TABLES.

============================================================
11. INDEXING
============================================================

Indexes improve the speed of data retrieval.

StockMaster uses:
- Primary key indexes.
- Unique indexes.
- Foreign key indexes.
- Composite indexes where required.

Important unique indexes include:
- users.email
- products.sku
- roles.role_name
- categories.category_name
- customers.email
- suppliers.email

The stock table has a composite unique index on:
(product_id, warehouse_id)

This prevents duplicate stock-balance records for the
same product in the same warehouse.

============================================================
12. COMMON TABLE EXPRESSIONS (CTEs)
============================================================

A CTE is a temporary named result set used within a query.

Example: Warehouse inventory summary.

WITH WarehouseSummary AS (
    SELECT
        w.warehouse_id,
        w.warehouse_name,
        SUM(st.quantity) AS total_units
    FROM warehouses w
    JOIN stock st
      ON w.warehouse_id = st.warehouse_id
    GROUP BY w.warehouse_id, w.warehouse_name
)
SELECT *
FROM WarehouseSummary
ORDER BY total_units DESC;

Testing:
A CTE was executed to calculate warehouse inventory totals
and inventory valuation.

============================================================
13. WINDOW FUNCTIONS
============================================================

Window functions perform calculations across related rows
without combining them into a single result row.

Example: Rank products by total stock.

SELECT
    p.product_name,
    SUM(st.quantity) AS total_stock,
    RANK() OVER (
        ORDER BY SUM(st.quantity) DESC
    ) AS stock_rank
FROM products p
JOIN stock st
  ON p.product_id = st.product_id
GROUP BY p.product_id, p.product_name;

Testing:
The RANK() window function was executed to rank products
according to their total stock quantities.

============================================================
14. APPLICATION-LEVEL SQL TRANSACTIONS
============================================================

StockMaster uses SQL transactions in important business operations.

Stock-In:
- Validates product and warehouse.
- Locks the relevant stock row.
- Increases inventory quantity.
- Records a stock movement.
- Commits the transaction.

Stock-Out:
- Checks available quantity.
- Prevents negative inventory.
- Decreases stock.
- Records the movement.
- Commits the transaction.

Purchase Order Receipt:
- Locks the purchase order.
- Updates stock quantities.
- Records stock movements.
- Changes the order status to Received.
- Commits the transaction.

Sales:
- Checks stock availability.
- Creates the sale and sale items.
- Reduces stock.
- Records stock-out movements.
- Commits the transaction.

Warehouse Transfer:
- Checks source inventory.
- Reduces source stock.
- Increases destination stock.
- Records transfer movements.
- Updates transfer status.
- Commits the transaction.

These operations use COMMIT and ROLLBACK to maintain
transaction consistency.

============================================================
15. SQL TESTING SUMMARY
============================================================

The following SQL topics were practised and tested:

1. DDL commands - CREATE, ALTER, TRUNCATE and DROP.
2. DML commands - INSERT, SELECT, UPDATE and DELETE.
3. DCL - GRANT and application database permissions.
4. TCL - COMMIT and ROLLBACK.
5. INNER JOIN.
6. LEFT JOIN.
7. RIGHT JOIN.
8. SELF JOIN.
9. Nested subqueries.
10. Correlated subqueries.
11. UNION.
12. INTERSECT.
13. EXCEPT.
14. Views.
15. Indexes.
16. CTEs.
17. Window functions.

The backend also uses parameterized SQL queries to reduce
SQL injection risk.

============================================================
16. CONCLUSION
============================================================

The StockMaster database demonstrates the practical
implementation of SQL concepts in a real-world inventory
management application.

The combination of relational queries, constraints,
transactions, views, indexes and advanced SQL operations
supports accurate inventory management and reporting.

The implementation provides the database functionality
required by the StockMaster project.
