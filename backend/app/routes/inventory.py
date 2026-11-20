from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required, roles_required

inventory_bp = Blueprint("inventory", __name__)


# GET: View inventory with optional filters and pagination
@inventory_bp.route("/", methods=["GET"])
@token_required
def get_inventory():
    cursor = None

    try:
        page = max(request.args.get("page", 1, type=int), 1)
        limit = request.args.get("limit", 10, type=int)

        if not 1 <= limit <= 100:
            return jsonify({
                "status": "error",
                "message": "Limit must be between 1 and 100"
            }), 400

        product_id = request.args.get("product_id", type=int)
        warehouse_id = request.args.get("warehouse_id", type=int)

        conditions = []
        params = []

        if product_id:
            conditions.append("s.product_id = %s")
            params.append(product_id)

        if warehouse_id:
            conditions.append("s.warehouse_id = %s")
            params.append(warehouse_id)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor = mysql.connection.cursor()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM stock s
            {where_clause}
            """,
            tuple(params)
        )

        total = cursor.fetchone()["total"]
        offset = (page - 1) * limit

        cursor.execute(
            f"""
            SELECT
                s.stock_id,
                s.product_id,
                p.product_name,
                p.sku,
                p.unit_price,
                p.reorder_level,
                s.warehouse_id,
                w.warehouse_name,
                s.quantity,
                s.updated_at,
                CASE
                    WHEN s.quantity <= p.reorder_level THEN 'LOW STOCK'
                    ELSE 'IN STOCK'
                END AS stock_status
            FROM stock s
            JOIN products p ON s.product_id = p.product_id
            JOIN warehouses w ON s.warehouse_id = w.warehouse_id
            {where_clause}
            ORDER BY s.stock_id
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )

        records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": records,
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
            "message": "Unable to retrieve inventory"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET: Stock for a particular product across warehouses
@inventory_bp.route("/product/<int:product_id>", methods=["GET"])
@token_required
def get_product_inventory(product_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                p.product_id,
                p.product_name,
                p.sku,
                p.reorder_level,
                w.warehouse_id,
                w.warehouse_name,
                COALESCE(s.quantity, 0) AS quantity
            FROM products p
            CROSS JOIN warehouses w
            LEFT JOIN stock s
                ON s.product_id = p.product_id
                AND s.warehouse_id = w.warehouse_id
            WHERE p.product_id = %s
            ORDER BY w.warehouse_id
        """, (product_id,))

        records = cursor.fetchall()

        if not records:
            return jsonify({
                "status": "error",
                "message": "Product not found"
            }), 404

        return jsonify({
            "status": "success",
            "data": records
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve product inventory"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET: Stock inside a particular warehouse
@inventory_bp.route("/warehouse/<int:warehouse_id>", methods=["GET"])
@token_required
def get_warehouse_inventory(warehouse_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT warehouse_id, warehouse_name FROM warehouses WHERE warehouse_id = %s",
            (warehouse_id,)
        )

        warehouse = cursor.fetchone()

        if not warehouse:
            return jsonify({
                "status": "error",
                "message": "Warehouse not found"
            }), 404

        cursor.execute("""
            SELECT
                p.product_id,
                p.product_name,
                p.sku,
                p.reorder_level,
                s.quantity,
                s.updated_at,
                CASE
                    WHEN s.quantity <= p.reorder_level THEN 'LOW STOCK'
                    ELSE 'IN STOCK'
                END AS stock_status
            FROM stock s
            JOIN products p ON s.product_id = p.product_id
            WHERE s.warehouse_id = %s
            ORDER BY p.product_name
        """, (warehouse_id,))

        records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "warehouse": warehouse,
            "data": records
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve warehouse inventory"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET: Low-stock records
@inventory_bp.route("/low-stock", methods=["GET"])
@token_required
def get_low_stock():
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                s.product_id,
                p.product_name,
                p.sku,
                s.warehouse_id,
                w.warehouse_name,
                s.quantity,
                p.reorder_level,
                (p.reorder_level - s.quantity) AS shortage
            FROM stock s
            JOIN products p ON s.product_id = p.product_id
            JOIN warehouses w ON s.warehouse_id = w.warehouse_id
            WHERE s.quantity <= p.reorder_level
            ORDER BY shortage DESC
        """)

        records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total": len(records),
            "data": records
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve low-stock records"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET: Stock movement history
@inventory_bp.route("/movements", methods=["GET"])
@token_required
def get_stock_movements():
    cursor = None

    try:
        page = max(request.args.get("page", 1, type=int), 1)
        limit = request.args.get("limit", 10, type=int)

        if not 1 <= limit <= 100:
            return jsonify({
                "status": "error",
                "message": "Limit must be between 1 and 100"
            }), 400

        product_id = request.args.get("product_id", type=int)
        warehouse_id = request.args.get("warehouse_id", type=int)
        movement_type = request.args.get("movement_type", "").upper()

        conditions = []
        params = []

        if product_id:
            conditions.append("sm.product_id = %s")
            params.append(product_id)

        if warehouse_id:
            conditions.append("sm.warehouse_id = %s")
            params.append(warehouse_id)

        if movement_type:
            allowed_types = {
                "IN", "OUT", "ADJUSTMENT", "TRANSFER_IN", "TRANSFER_OUT"
            }

            if movement_type not in allowed_types:
                return jsonify({
                    "status": "error",
                    "message": "Invalid movement type"
                }), 400

            conditions.append("sm.movement_type = %s")
            params.append(movement_type)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor = mysql.connection.cursor()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM stock_movements sm
            {where_clause}
            """,
            tuple(params)
        )

        total = cursor.fetchone()["total"]
        offset = (page - 1) * limit

        cursor.execute(
            f"""
            SELECT
                sm.movement_id,
                sm.product_id,
                p.product_name,
                sm.warehouse_id,
                w.warehouse_name,
                sm.movement_type,
                sm.quantity,
                sm.reference_note,
                sm.performed_by,
                u.full_name AS performed_by_name,
                sm.movement_date
            FROM stock_movements sm
            JOIN products p ON sm.product_id = p.product_id
            JOIN warehouses w ON sm.warehouse_id = w.warehouse_id
            LEFT JOIN users u ON sm.performed_by = u.user_id
            {where_clause}
            ORDER BY sm.movement_date DESC, sm.movement_id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )

        records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": records,
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
            "message": "Unable to retrieve stock movements"
        }), 500

    finally:
        if cursor:
            cursor.close()


# POST: Stock IN
@inventory_bp.route("/stock-in", methods=["POST"])
@roles_required("Admin", "Manager", "Staff")
def stock_in():
    return update_stock("IN")


# POST: Stock OUT
@inventory_bp.route("/stock-out", methods=["POST"])
@roles_required("Admin", "Manager", "Staff")
def stock_out():
    return update_stock("OUT")


# POST: Stock adjustment (Admin and Manager only)
@inventory_bp.route("/adjustment", methods=["POST"])
@roles_required("Admin", "Manager")
def stock_adjustment():
    return update_stock("ADJUSTMENT")


def update_stock(movement_type):
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        product_id = data.get("product_id")
        warehouse_id = data.get("warehouse_id")
        reference_note = data.get("reference_note", "")

        if (
            isinstance(product_id, bool)
            or isinstance(warehouse_id, bool)
        ):
            return jsonify({
                "status": "error",
                "message": "Product ID and warehouse ID must be valid integers"
            }), 400

        try:
            product_id = int(product_id)
            warehouse_id = int(warehouse_id)
        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Product ID and warehouse ID are required"
            }), 400

        if product_id < 1 or warehouse_id < 1:
            return jsonify({
                "status": "error",
                "message": "Invalid product or warehouse ID"
            }), 400

        if not isinstance(reference_note, str):
            return jsonify({
                "status": "error",
                "message": "Reference note must be text"
            }), 400

        if movement_type == "ADJUSTMENT":
            new_quantity = data.get("new_quantity")

            if isinstance(new_quantity, bool):
                return jsonify({
                    "status": "error",
                    "message": "New quantity must be a non-negative integer"
                }), 400

            try:
                new_quantity = int(new_quantity)
                if new_quantity < 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return jsonify({
                    "status": "error",
                    "message": "A valid non-negative new_quantity is required"
                }), 400

        else:
            quantity = data.get("quantity")

            if isinstance(quantity, bool):
                return jsonify({
                    "status": "error",
                    "message": "Quantity must be a positive integer"
                }), 400

            try:
                quantity = int(quantity)
                if quantity <= 0:
                    raise ValueError()
            except (ValueError, TypeError):
                return jsonify({
                    "status": "error",
                    "message": "A valid positive quantity is required"
                }), 400

        cursor = mysql.connection.cursor()
        cursor.execute("START TRANSACTION")

        # Validate product and warehouse
        cursor.execute(
            "SELECT product_id FROM products WHERE product_id = %s",
            (product_id,)
        )
        if not cursor.fetchone():
            mysql.connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Product not found"
            }), 404

        cursor.execute(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id = %s",
            (warehouse_id,)
        )
        if not cursor.fetchone():
            mysql.connection.rollback()
            return jsonify({
                "status": "error",
                "message": "Warehouse not found"
            }), 404

        # Create a zero-stock row if it does not exist.
        # The unique product/warehouse key prevents duplicate balances.
        cursor.execute("""
            INSERT INTO stock (product_id, warehouse_id, quantity)
            VALUES (%s, %s, 0)
            ON DUPLICATE KEY UPDATE quantity = quantity
        """, (product_id, warehouse_id))

        # Lock the stock row to prevent concurrent updates.
        cursor.execute("""
            SELECT quantity
            FROM stock
            WHERE product_id = %s AND warehouse_id = %s
            FOR UPDATE
        """, (product_id, warehouse_id))

        stock_record = cursor.fetchone()
        old_quantity = int(stock_record["quantity"])

        if movement_type == "IN":
            new_stock_quantity = old_quantity + quantity
            movement_quantity = quantity

        elif movement_type == "OUT":
            if old_quantity < quantity:
                mysql.connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": "Insufficient stock",
                    "available_quantity": old_quantity
                }), 409

            new_stock_quantity = old_quantity - quantity
            movement_quantity = quantity

        else:
            new_stock_quantity = new_quantity
            movement_quantity = abs(new_quantity - old_quantity)

            if movement_quantity == 0:
                mysql.connection.rollback()
                return jsonify({
                    "status": "error",
                    "message": "Stock already has the requested quantity"
                }), 400

            reference_note = (
                f"{reference_note} | Stock adjusted from "
                f"{old_quantity} to {new_quantity}"
            ).strip(" |")

        cursor.execute("""
            UPDATE stock
            SET quantity = %s
            WHERE product_id = %s AND warehouse_id = %s
        """, (
            new_stock_quantity,
            product_id,
            warehouse_id
        ))

        cursor.execute("""
            INSERT INTO stock_movements
                (product_id, warehouse_id, movement_type,
                 quantity, reference_note, performed_by)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            product_id,
            warehouse_id,
            movement_type,
            movement_quantity,
            reference_note or None,
            request.current_user["user_id"]
        ))

        movement_id = cursor.lastrowid
        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": f"Stock {movement_type.lower()} completed successfully",
            "data": {
                "movement_id": movement_id,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "movement_type": movement_type,
                "previous_quantity": old_quantity,
                "movement_quantity": movement_quantity,
                "new_quantity": new_stock_quantity
            }
        }), 200

    except Exception:
        mysql.connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Unable to update stock. No changes were committed."
        }), 500

    finally:
        if cursor:
            cursor.close()
