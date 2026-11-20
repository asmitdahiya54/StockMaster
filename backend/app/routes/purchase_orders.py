from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required, roles_required

purchase_orders_bp = Blueprint("purchase_orders", __name__)


# GET ALL PURCHASE ORDERS
@purchase_orders_bp.route("/", methods=["GET"])
@token_required
def get_purchase_orders():
    cursor = None
    try:
        page = max(request.args.get("page", 1, type=int), 1)
        limit = min(max(request.args.get("limit", 10, type=int), 1), 100)
        offset = (page - 1) * limit

        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                po.purchase_order_id,
                po.order_date,
                po.expected_date,
                po.status,
                s.supplier_name,
                w.warehouse_name,
                u.full_name AS created_by_name,
                COUNT(poi.purchase_item_id) AS item_count,
                COALESCE(SUM(poi.quantity), 0) AS total_quantity,
                COALESCE(SUM(poi.quantity * poi.unit_cost), 0) AS total_cost
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            JOIN warehouses w ON po.warehouse_id = w.warehouse_id
            JOIN users u ON po.created_by = u.user_id
            LEFT JOIN purchase_order_items poi
                ON po.purchase_order_id = poi.purchase_order_id
            GROUP BY
                po.purchase_order_id,
                po.order_date,
                po.expected_date,
                po.status,
                s.supplier_name,
                w.warehouse_name,
                u.full_name
            ORDER BY po.purchase_order_id DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))

        orders = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS total FROM purchase_orders")
        total = cursor.fetchone()["total"]

        return jsonify({
            "status": "success",
            "data": orders,
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
            "message": "Unable to retrieve purchase orders"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET PURCHASE ORDER BY ID WITH ITEMS
@purchase_orders_bp.route("/<int:order_id>", methods=["GET"])
@token_required
def get_purchase_order(order_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                po.purchase_order_id,
                po.supplier_id,
                s.supplier_name,
                po.warehouse_id,
                w.warehouse_name,
                po.created_by,
                u.full_name AS created_by_name,
                po.order_date,
                po.expected_date,
                po.status
            FROM purchase_orders po
            JOIN suppliers s ON po.supplier_id = s.supplier_id
            JOIN warehouses w ON po.warehouse_id = w.warehouse_id
            JOIN users u ON po.created_by = u.user_id
            WHERE po.purchase_order_id = %s
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            return jsonify({
                "status": "error",
                "message": "Purchase order not found"
            }), 404

        cursor.execute("""
            SELECT
                poi.purchase_item_id,
                poi.product_id,
                p.product_name,
                p.sku,
                poi.quantity,
                poi.unit_cost,
                (poi.quantity * poi.unit_cost) AS line_total
            FROM purchase_order_items poi
            JOIN products p ON poi.product_id = p.product_id
            WHERE poi.purchase_order_id = %s
            ORDER BY poi.purchase_item_id
        """, (order_id,))

        order["items"] = cursor.fetchall()

        order["item_count"] = len(order["items"])
        order["total_quantity"] = sum(
            item["quantity"] for item in order["items"]
        )
        order["total_cost"] = sum(
            float(item["line_total"]) for item in order["items"]
        )

        return jsonify({
            "status": "success",
            "data": order
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve purchase order"
        }), 500

    finally:
        if cursor:
            cursor.close()

# CREATE PURCHASE ORDER
@purchase_orders_bp.route("/", methods=["POST"])
@roles_required("Admin", "Manager")
def create_purchase_order():
    from datetime import datetime
    from decimal import Decimal, InvalidOperation

    data = request.get_json(silent=True) or {}

    supplier_id = data.get("supplier_id")
    warehouse_id = data.get("warehouse_id")
    expected_date = data.get("expected_date")
    items = data.get("items")

    # BASIC VALIDATION
    if not isinstance(supplier_id, int) or isinstance(supplier_id, bool) or supplier_id <= 0:
        return jsonify({"status": "error", "message": "Valid supplier_id is required"}), 400

    if not isinstance(warehouse_id, int) or isinstance(warehouse_id, bool) or warehouse_id <= 0:
        return jsonify({"status": "error", "message": "Valid warehouse_id is required"}), 400

    if expected_date is not None:
        if not isinstance(expected_date, str):
            return jsonify({"status": "error", "message": "Invalid expected_date"}), 400
        try:
            datetime.strptime(expected_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"status": "error", "message": "Date must use YYYY-MM-DD format"}), 400

    if not isinstance(items, list) or not items:
        return jsonify({"status": "error", "message": "At least one product item is required"}), 400

    if len(items) > 100:
        return jsonify({"status": "error", "message": "Maximum 100 items allowed"}), 400

    validated_items = []
    seen_products = set()

    for item in items:
        if not isinstance(item, dict):
            return jsonify({"status": "error", "message": "Each item must be an object"}), 400

        product_id = item.get("product_id")
        quantity = item.get("quantity")
        unit_cost = item.get("unit_cost")

        if not isinstance(product_id, int) or isinstance(product_id, bool) or product_id <= 0:
            return jsonify({"status": "error", "message": "Every item needs a valid product_id"}), 400

        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            return jsonify({"status": "error", "message": "Quantity must be a positive integer"}), 400

        if product_id in seen_products:
            return jsonify({"status": "error", "message": "Duplicate products are not allowed in one order"}), 400

        try:
            cost = Decimal(str(unit_cost))
            if not cost.is_finite() or cost <= 0 or cost.as_tuple().exponent < -2:
                raise ValueError()
        except (InvalidOperation, ValueError, TypeError):
            return jsonify({"status": "error", "message": "Unit cost must be a positive amount with up to 2 decimal places"}), 400

        seen_products.add(product_id)
        validated_items.append((product_id, quantity, cost))

    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("START TRANSACTION")

        # VERIFY SUPPLIER
        cursor.execute(
            "SELECT supplier_id FROM suppliers WHERE supplier_id = %s",
            (supplier_id,)
        )
        if not cursor.fetchone():
            mysql.connection.rollback()
            return jsonify({"status": "error", "message": "Supplier not found"}), 404

        # VERIFY WAREHOUSE
        cursor.execute(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id = %s",
            (warehouse_id,)
        )
        if not cursor.fetchone():
            mysql.connection.rollback()
            return jsonify({"status": "error", "message": "Warehouse not found"}), 404

        # VERIFY ALL PRODUCTS
        for product_id, quantity, cost in validated_items:
            cursor.execute(
                "SELECT product_id FROM products WHERE product_id = %s",
                (product_id,)
            )
            if not cursor.fetchone():
                mysql.connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": f"Product ID {product_id} not found"
                }), 404

        # CREATE PURCHASE ORDER
        cursor.execute("""
            INSERT INTO purchase_orders
                (supplier_id, warehouse_id, created_by, order_date, expected_date, status)
            VALUES (%s, %s, %s, CURDATE(), %s, 'Pending')
        """, (
            supplier_id,
            warehouse_id,
            request.current_user["user_id"],
            expected_date
        ))

        order_id = cursor.lastrowid

        # INSERT PURCHASE ORDER ITEMS
        for product_id, quantity, cost in validated_items:
            cursor.execute("""
                INSERT INTO purchase_order_items
                    (purchase_order_id, product_id, quantity, unit_cost)
                VALUES (%s, %s, %s, %s)
            """, (order_id, product_id, quantity, cost))

        mysql.connection.commit()

        total_quantity = sum(item[1] for item in validated_items)
        total_cost = sum(
            (item[1] * item[2] for item in validated_items),
            Decimal("0.00")
        )

        return jsonify({
            "status": "success",
            "message": "Purchase order created successfully",
            "data": {
                "purchase_order_id": order_id,
                "supplier_id": supplier_id,
                "warehouse_id": warehouse_id,
                "status": "Pending",
                "total_items": len(validated_items),
                "total_quantity": total_quantity,
                "total_cost": str(total_cost)
            }
        }), 201

    except Exception:
        mysql.connection.rollback()
        return jsonify({
            "status": "error",
            "message": "Unable to create purchase order"
        }), 500

    finally:
        if cursor:
            cursor.close()


# RECEIVE PURCHASE ORDER
@purchase_orders_bp.route("/<int:order_id>/receive", methods=["POST"])
@roles_required("Admin", "Manager")
def receive_purchase_order(order_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        # START TRANSACTION
        cursor.execute("START TRANSACTION")

        # LOCK AND VERIFY PURCHASE ORDER
        cursor.execute("""
            SELECT purchase_order_id, warehouse_id, status
            FROM purchase_orders
            WHERE purchase_order_id = %s
            FOR UPDATE
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            mysql.connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Purchase order not found"
            }), 404

        if order["status"] != "Pending":
            mysql.connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Only Pending purchase orders can be received"
            }), 409

        warehouse_id = order["warehouse_id"]
        performed_by = request.current_user["user_id"]

        # FETCH PURCHASE ORDER ITEMS
        cursor.execute("""
            SELECT product_id, quantity
            FROM purchase_order_items
            WHERE purchase_order_id = %s
        """, (order_id,))

        items = cursor.fetchall()

        if not items:
            mysql.connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Purchase order has no items"
            }), 400

        received_items = []

        # UPDATE STOCK AND CREATE MOVEMENT RECORDS
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            # Ensure stock row exists.
            # IGNORE handles an existing product/warehouse combination.
            cursor.execute("""
                INSERT IGNORE INTO stock
                    (product_id, warehouse_id, quantity, updated_at)
                VALUES (%s, %s, 0, NOW())
            """, (product_id, warehouse_id))

            # Lock the stock record.
            cursor.execute("""
                SELECT quantity
                FROM stock
                WHERE product_id = %s AND warehouse_id = %s
                FOR UPDATE
            """, (product_id, warehouse_id))

            stock_record = cursor.fetchone()

            if not stock_record:
                raise Exception("Unable to create or locate stock record")

            # Increase inventory.
            cursor.execute("""
                UPDATE stock
                SET quantity = quantity + %s,
                    updated_at = NOW()
                WHERE product_id = %s AND warehouse_id = %s
            """, (quantity, product_id, warehouse_id))

            # Record stock movement.
            cursor.execute("""
                INSERT INTO stock_movements
                    (product_id, warehouse_id, movement_type,
                     quantity, reference_note, performed_by, movement_date)
                VALUES (%s, %s, 'IN', %s, %s, %s, NOW())
            """, (
                product_id,
                warehouse_id,
                quantity,
                f"Purchase Order #{order_id} received",
                performed_by
            ))

            received_items.append({
                "product_id": product_id,
                "quantity_received": quantity,
                "previous_stock": stock_record["quantity"],
                "new_stock": stock_record["quantity"] + quantity
            })

        # UPDATE PURCHASE ORDER STATUS
        cursor.execute("""
            UPDATE purchase_orders
            SET status = 'Received'
            WHERE purchase_order_id = %s
        """, (order_id,))

        # COMMIT ALL CHANGES
        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Purchase order received successfully",
            "data": {
                "purchase_order_id": order_id,
                "status": "Received",
                "warehouse_id": warehouse_id,
                "items_received": len(received_items),
                "items": received_items
            }
        }), 200

    except Exception:
        mysql.connection.rollback()
        return jsonify({
            "status": "error",
            "message": "Unable to receive purchase order"
        }), 500

    finally:
        if cursor:
            cursor.close()

