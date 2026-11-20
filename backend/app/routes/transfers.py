from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required, roles_required
from decimal import Decimal, InvalidOperation

transfers_bp = Blueprint("transfers", __name__)


@transfers_bp.route("/", methods=["GET"])
@token_required
def get_transfers():
    cursor = None
    try:
        page = max(request.args.get("page", 1, type=int), 1)
        limit = min(max(request.args.get("limit", 10, type=int), 1), 100)
        offset = (page - 1) * limit
        search = request.args.get("search", "").strip()
        status = request.args.get("status", "").strip()

        conditions = []
        params = []

        if search:
            conditions.append("""
                (
                    CAST(wt.transfer_id AS CHAR) LIKE %s
                    OR source.warehouse_name LIKE %s
                    OR destination.warehouse_name LIKE %s
                )
            """)
            term = f"%{search}%"
            params.extend([term, term, term])

        if status:
            conditions.append("wt.status = %s")
            params.append(status)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        cursor = mysql.connection.cursor()

        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM warehouse_transfers wt
            JOIN warehouses source ON wt.source_warehouse_id = source.warehouse_id
            JOIN warehouses destination ON wt.destination_warehouse_id = destination.warehouse_id
            {where_clause}
        """, tuple(params))

        total = cursor.fetchone()["total"]

        cursor.execute(f"""
            SELECT
                wt.transfer_id,
                wt.source_warehouse_id,
                source.warehouse_name AS source_warehouse,
                wt.destination_warehouse_id,
                destination.warehouse_name AS destination_warehouse,
                wt.transferred_by,
                u.full_name AS transferred_by_name,
                wt.transfer_date,
                wt.status,
                COALESCE(items.item_count, 0) AS item_count,
                COALESCE(items.total_quantity, 0) AS total_quantity
            FROM warehouse_transfers wt
            JOIN warehouses source ON wt.source_warehouse_id = source.warehouse_id
            JOIN warehouses destination ON wt.destination_warehouse_id = destination.warehouse_id
            JOIN users u ON wt.transferred_by = u.user_id
            LEFT JOIN (
                SELECT transfer_id, COUNT(*) AS item_count, SUM(quantity) AS total_quantity
                FROM transfer_items
                GROUP BY transfer_id
            ) items ON wt.transfer_id = items.transfer_id
            {where_clause}
            ORDER BY wt.transfer_id DESC
            LIMIT %s OFFSET %s
        """, tuple(params + [limit, offset]))

        transfers = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": transfers,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_records": total,
                "total_pages": (total + limit - 1) // limit
            }
        }), 200

    except Exception:
        return jsonify({"status": "error", "message": "Unable to retrieve transfers"}), 500
    finally:
        if cursor:
            cursor.close()


@transfers_bp.route("/<int:transfer_id>", methods=["GET"])
@token_required
def get_transfer_details(transfer_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                wt.transfer_id,
                wt.source_warehouse_id,
                source.warehouse_name AS source_warehouse,
                wt.destination_warehouse_id,
                destination.warehouse_name AS destination_warehouse,
                wt.transferred_by,
                u.full_name AS transferred_by_name,
                wt.transfer_date,
                wt.status
            FROM warehouse_transfers wt
            JOIN warehouses source ON wt.source_warehouse_id = source.warehouse_id
            JOIN warehouses destination ON wt.destination_warehouse_id = destination.warehouse_id
            JOIN users u ON wt.transferred_by = u.user_id
            WHERE wt.transfer_id = %s
            LIMIT 1
        """, (transfer_id,))

        transfer = cursor.fetchone()

        if not transfer:
            return jsonify({"status": "error", "message": "Warehouse transfer not found"}), 404

        cursor.execute("""
            SELECT
                ti.transfer_item_id,
                ti.product_id,
                p.product_name,
                p.sku,
                ti.quantity
            FROM transfer_items ti
            JOIN products p ON ti.product_id = p.product_id
            WHERE ti.transfer_id = %s
            ORDER BY ti.transfer_item_id
        """, (transfer_id,))

        items = cursor.fetchall()
        transfer["items"] = items
        transfer["item_count"] = len(items)
        transfer["total_quantity"] = sum(item["quantity"] for item in items)

        return jsonify({"status": "success", "data": transfer}), 200

    except Exception:
        return jsonify({"status": "error", "message": "Unable to retrieve transfer details"}), 500
    finally:
        if cursor:
            cursor.close()


@transfers_bp.route("/", methods=["POST"])
@roles_required("Admin", "Manager")
def create_transfer():
    data = request.get_json(silent=True) or {}

    source_id = data.get("source_warehouse_id")
    destination_id = data.get("destination_warehouse_id")
    items = data.get("items")

    if not isinstance(source_id, int) or isinstance(source_id, bool) or source_id <= 0:
        return jsonify({"status": "error", "message": "Valid source warehouse ID required"}), 400

    if not isinstance(destination_id, int) or isinstance(destination_id, bool) or destination_id <= 0:
        return jsonify({"status": "error", "message": "Valid destination warehouse ID required"}), 400

    if source_id == destination_id:
        return jsonify({"status": "error", "message": "Source and destination warehouses must be different"}), 400

    if not isinstance(items, list) or not items:
        return jsonify({"status": "error", "message": "At least one transfer item is required"}), 400

    normalized_items = []
    seen_products = set()

    for item in items:
        if not isinstance(item, dict):
            return jsonify({"status": "error", "message": "Invalid transfer item"}), 400

        product_id = item.get("product_id")
        quantity = item.get("quantity")

        if not isinstance(product_id, int) or isinstance(product_id, bool) or product_id <= 0:
            return jsonify({"status": "error", "message": "Valid product ID required"}), 400

        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
            return jsonify({"status": "error", "message": "Quantity must be a positive integer"}), 400

        if product_id in seen_products:
            return jsonify({"status": "error", "message": "Duplicate products are not allowed"}), 400

        seen_products.add(product_id)
        normalized_items.append((product_id, quantity))

    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("START TRANSACTION")

        cursor.execute(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id IN (%s, %s) FOR UPDATE",
            (source_id, destination_id)
        )
        warehouse_ids = {row["warehouse_id"] for row in cursor.fetchall()}

        if source_id not in warehouse_ids or destination_id not in warehouse_ids:
            mysql.connection.rollback()
            return jsonify({"status": "error", "message": "Source or destination warehouse not found"}), 404

        for product_id, quantity in normalized_items:
            cursor.execute(
                "SELECT product_id FROM products WHERE product_id = %s",
                (product_id,)
            )
            if not cursor.fetchone():
                mysql.connection.rollback()
                return jsonify({"status": "error", "message": f"Product ID {product_id} not found"}), 404

        for product_id, quantity in normalized_items:
            cursor.execute("""
                SELECT quantity
                FROM stock
                WHERE product_id = %s AND warehouse_id = %s
                FOR UPDATE
            """, (product_id, source_id))

            row = cursor.fetchone()
            available = row["quantity"] if row else 0

            if available < quantity:
                mysql.connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": "Insufficient source stock",
                    "product_id": product_id,
                    "available": available,
                    "requested": quantity
                }), 409

        cursor.execute("""
            INSERT INTO warehouse_transfers
                (source_warehouse_id, destination_warehouse_id, transferred_by, status)
            VALUES (%s, %s, %s, 'Pending')
        """, (
            source_id,
            destination_id,
            request.current_user["user_id"]
        ))

        transfer_id = cursor.lastrowid

        for product_id, quantity in normalized_items:
            cursor.execute("""
                INSERT INTO transfer_items (transfer_id, product_id, quantity)
                VALUES (%s, %s, %s)
            """, (transfer_id, product_id, quantity))

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Warehouse transfer created successfully",
            "data": {
                "transfer_id": transfer_id,
                "status": "Pending",
                "source_warehouse_id": source_id,
                "destination_warehouse_id": destination_id,
                "items": [
                    {"product_id": product_id, "quantity": quantity}
                    for product_id, quantity in normalized_items
                ]
            }
        }), 201

    except Exception:
        if cursor:
            mysql.connection.rollback()
        return jsonify({"status": "error", "message": "Unable to create warehouse transfer"}), 500
    finally:
        if cursor:
            cursor.close()


@transfers_bp.route("/<int:transfer_id>/complete", methods=["POST"])
@roles_required("Admin", "Manager")
def complete_transfer(transfer_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("START TRANSACTION")

        cursor.execute("""
            SELECT transfer_id, source_warehouse_id, destination_warehouse_id, status
            FROM warehouse_transfers
            WHERE transfer_id = %s
            FOR UPDATE
        """, (transfer_id,))

        transfer = cursor.fetchone()

        if not transfer:
            mysql.connection.rollback()
            return jsonify({"status": "error", "message": "Warehouse transfer not found"}), 404

        if transfer["status"] != "Pending":
            mysql.connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Only pending transfers can be completed",
                "current_status": transfer["status"]
            }), 409

        source_id = transfer["source_warehouse_id"]
        destination_id = transfer["destination_warehouse_id"]
        user_id = request.current_user["user_id"]

        cursor.execute("""
            SELECT product_id, quantity
            FROM transfer_items
            WHERE transfer_id = %s
            ORDER BY product_id
        """, (transfer_id,))

        items = cursor.fetchall()

        if not items:
            mysql.connection.rollback()
            return jsonify({"status": "error", "message": "Transfer has no items"}), 400

        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            cursor.execute("""
                SELECT quantity
                FROM stock
                WHERE product_id = %s AND warehouse_id = %s
                FOR UPDATE
            """, (product_id, source_id))

            source_stock = cursor.fetchone()
            available = source_stock["quantity"] if source_stock else 0

            if available < quantity:
                mysql.connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": "Insufficient source stock to complete transfer",
                    "product_id": product_id,
                    "available": available,
                    "requested": quantity
                }), 409

        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            cursor.execute("""
                UPDATE stock
                SET quantity = quantity - %s
                WHERE product_id = %s AND warehouse_id = %s
            """, (quantity, product_id, source_id))

            cursor.execute("""
                INSERT INTO stock (product_id, warehouse_id, quantity)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity = quantity + VALUES(quantity)
            """, (product_id, destination_id, quantity))

            reference = f"Warehouse Transfer #{transfer_id}"

            cursor.execute("""
                INSERT INTO stock_movements
                    (product_id, warehouse_id, movement_type, quantity, reference_note, performed_by)
                VALUES (%s, %s, 'TRANSFER_OUT', %s, %s, %s)
            """, (product_id, source_id, quantity, reference, user_id))

            cursor.execute("""
                INSERT INTO stock_movements
                    (product_id, warehouse_id, movement_type, quantity, reference_note, performed_by)
                VALUES (%s, %s, 'TRANSFER_IN', %s, %s, %s)
            """, (product_id, destination_id, quantity, reference, user_id))

        cursor.execute("""
            UPDATE warehouse_transfers
            SET status = 'Completed'
            WHERE transfer_id = %s
        """, (transfer_id,))

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Warehouse transfer completed successfully",
            "data": {
                "transfer_id": transfer_id,
                "status": "Completed",
                "items_processed": len(items)
            }
        }), 200

    except Exception:
        if cursor:
            mysql.connection.rollback()
        return jsonify({"status": "error", "message": "Unable to complete warehouse transfer"}), 500
    finally:
        if cursor:
            cursor.close()
