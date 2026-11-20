from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required, roles_required

sales_bp = Blueprint("sales", __name__)


# GET ALL SALES
@sales_bp.route("/", methods=["GET"])
@token_required
def get_sales():
    cursor = None

    try:
        page = max(request.args.get("page", 1, type=int), 1)
        limit = min(max(request.args.get("limit", 10, type=int), 1), 100)
        offset = (page - 1) * limit
        search = request.args.get("search", "").strip()
        status = request.args.get("status", "").strip()

        cursor = mysql.connection.cursor()

        conditions = []
        params = []

        if search:
            conditions.append("""
                (c.customer_name LIKE %s
                OR CAST(s.sale_id AS CHAR) LIKE %s)
            """)
            params.extend([f"%{search}%", f"%{search}%"])

        if status:
            conditions.append("s.status = %s")
            params.append(status)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        query = f"""
            SELECT
                s.sale_id,
                s.sale_date,
                s.status,
                c.customer_id,
                c.customer_name,
                w.warehouse_id,
                w.warehouse_name,
                u.full_name AS sold_by_name,
                COUNT(si.sale_item_id) AS item_count,
                COALESCE(SUM(si.quantity), 0) AS total_quantity,
                COALESCE(SUM(si.quantity * si.unit_price), 0) AS total_amount
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            JOIN warehouses w ON s.warehouse_id = w.warehouse_id
            JOIN users u ON s.sold_by = u.user_id
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
            {where_clause}
            GROUP BY
                s.sale_id,
                s.sale_date,
                s.status,
                c.customer_id,
                c.customer_name,
                w.warehouse_id,
                w.warehouse_name,
                u.full_name
            ORDER BY s.sale_id DESC
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, tuple(params + [limit, offset]))
        sales = cursor.fetchall()

        count_query = f"""
            SELECT COUNT(*) AS total
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            {where_clause}
        """

        cursor.execute(count_query, tuple(params))
        total = cursor.fetchone()["total"]

        return jsonify({
            "status": "success",
            "data": sales,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total,
                "total_pages": (total + limit - 1) // limit
            }
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve sales"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET SALE DETAILS BY ID
@sales_bp.route("/<int:sale_id>", methods=["GET"])
@token_required
def get_sale(sale_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                s.sale_id,
                s.customer_id,
                c.customer_name,
                c.customer_type,
                s.warehouse_id,
                w.warehouse_name,
                s.sold_by,
                u.full_name AS sold_by_name,
                s.sale_date,
                s.status
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            JOIN warehouses w ON s.warehouse_id = w.warehouse_id
            JOIN users u ON s.sold_by = u.user_id
            WHERE s.sale_id = %s
        """, (sale_id,))

        sale = cursor.fetchone()

        if not sale:
            return jsonify({
                "status": "error",
                "message": "Sale not found"
            }), 404

        cursor.execute("""
            SELECT
                si.sale_item_id,
                si.product_id,
                p.product_name,
                p.sku,
                si.quantity,
                si.unit_price,
                (si.quantity * si.unit_price) AS line_total
            FROM sale_items si
            JOIN products p ON si.product_id = p.product_id
            WHERE si.sale_id = %s
            ORDER BY si.sale_item_id
        """, (sale_id,))

        sale["items"] = cursor.fetchall()

        sale["item_count"] = len(sale["items"])
        sale["total_quantity"] = sum(
            item["quantity"] for item in sale["items"]
        )
        sale["total_amount"] = sum(
            float(item["line_total"]) for item in sale["items"]
        )

        return jsonify({
            "status": "success",
            "data": sale
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve sale details"
        }), 500

    finally:
        if cursor:
            cursor.close()

# CREATE SALE
@sales_bp.route("/", methods=["POST"])
@roles_required("Admin", "Manager", "Staff")
def create_sale():
    from decimal import Decimal, InvalidOperation

    data = request.get_json(silent=True) or {}

    customer_id = data.get("customer_id")
    warehouse_id = data.get("warehouse_id")
    items = data.get("items")

    if not isinstance(customer_id, int) or isinstance(customer_id, bool) or customer_id <= 0:
        return jsonify({"status": "error", "message": "Valid customer_id is required"}), 400

    if not isinstance(warehouse_id, int) or isinstance(warehouse_id, bool) or warehouse_id <= 0:
        return jsonify({"status": "error", "message": "Valid warehouse_id is required"}), 400

    if not isinstance(items, list) or not items:
        return jsonify({"status": "error", "message": "At least one product is required"}), 400

    if len(items) > 100:
        return jsonify({"status": "error", "message": "Maximum 100 items allowed"}), 400

    validated_items = []
    seen_products = set()

    for item in items:
        if not isinstance(item, dict):
            return jsonify({"status": "error", "message": "Each item must be an object"}), 400

        product_id = item.get("product_id")
        quantity = item.get("quantity")
        unit_price = item.get("unit_price")

        if not isinstance(product_id, int) or isinstance(product_id, bool) or product_id <= 0:
            return jsonify({"status": "error", "message": "Invalid product_id"}), 400

        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            return jsonify({"status": "error", "message": "Quantity must be a positive integer"}), 400

        if product_id in seen_products:
            return jsonify({"status": "error", "message": "Duplicate products are not allowed"}), 400

        try:
            price = Decimal(str(unit_price))
            if not price.is_finite() or price <= 0 or price.as_tuple().exponent < -2:
                raise ValueError()
        except (InvalidOperation, ValueError, TypeError):
            return jsonify({"status": "error", "message": "Unit price must be positive with up to 2 decimal places"}), 400

        seen_products.add(product_id)
        validated_items.append((product_id, quantity, price))

    cursor = None

    try:
        cursor = mysql.connection.cursor()
        cursor.execute("START TRANSACTION")

        # VERIFY CUSTOMER
        cursor.execute(
            "SELECT customer_id FROM customers WHERE customer_id = %s",
            (customer_id,)
        )

        if not cursor.fetchone():
            mysql.connection.rollback()
            return jsonify({"status": "error", "message": "Customer not found"}), 404

        # VERIFY WAREHOUSE
        cursor.execute(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id = %s",
            (warehouse_id,)
        )

        if not cursor.fetchone():
            mysql.connection.rollback()
            return jsonify({"status": "error", "message": "Warehouse not found"}), 404

        # CHECK ALL PRODUCTS AND STOCK
        stock_details = []

        for product_id, quantity, price in validated_items:
            cursor.execute("""
                SELECT p.product_id, p.product_name, s.quantity
                FROM products p
                LEFT JOIN stock s
                    ON p.product_id = s.product_id
                    AND s.warehouse_id = %s
                WHERE p.product_id = %s
                FOR UPDATE
            """, (warehouse_id, product_id))

            product = cursor.fetchone()

            if not product:
                mysql.connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": f"Product ID {product_id} not found"
                }), 404

            available = product["quantity"] if product["quantity"] is not None else 0

            if available < quantity:
                mysql.connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": "Insufficient stock",
                    "product": product["product_name"],
                    "available": available,
                    "requested": quantity
                }), 409

            stock_details.append({
                "product_id": product_id,
                "quantity": quantity,
                "available": available,
                "price": price
            })

        # CREATE SALE
        cursor.execute("""
            INSERT INTO sales
                (customer_id, warehouse_id, sold_by, sale_date, status)
            VALUES (%s, %s, %s, NOW(), 'Completed')
        """, (
            customer_id,
            warehouse_id,
            request.current_user["user_id"]
        ))

        sale_id = cursor.lastrowid

        total_quantity = 0
        total_amount = Decimal("0.00")

        # INSERT SALE ITEMS, DEDUCT STOCK AND RECORD MOVEMENTS
        for item in stock_details:
            product_id = item["product_id"]
            quantity = item["quantity"]
            price = item["price"]

            cursor.execute("""
                INSERT INTO sale_items
                    (sale_id, product_id, quantity, unit_price)
                VALUES (%s, %s, %s, %s)
            """, (sale_id, product_id, quantity, price))

            cursor.execute("""
                UPDATE stock
                SET quantity = quantity - %s,
                    updated_at = NOW()
                WHERE product_id = %s
                    AND warehouse_id = %s
                    AND quantity >= %s
            """, (quantity, product_id, warehouse_id, quantity))

            if cursor.rowcount != 1:
                raise Exception("Stock changed during sale processing")

            cursor.execute("""
                INSERT INTO stock_movements
                    (product_id, warehouse_id, movement_type,
                     quantity, reference_note, performed_by, movement_date)
                VALUES (%s, %s, 'OUT', %s, %s, %s, NOW())
            """, (
                product_id,
                warehouse_id,
                quantity,
                f"Sale #{sale_id}",
                request.current_user["user_id"]
            ))

            total_quantity += quantity
            total_amount += quantity * price

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Sale created successfully",
            "data": {
                "sale_id": sale_id,
                "customer_id": customer_id,
                "warehouse_id": warehouse_id,
                "status": "Completed",
                "total_items": len(validated_items),
                "total_quantity": total_quantity,
                "total_amount": str(total_amount)
            }
        }), 201

    except Exception:
        mysql.connection.rollback()
        return jsonify({
            "status": "error",
            "message": "Unable to create sale"
        }), 500

    finally:
        if cursor:
            cursor.close()

