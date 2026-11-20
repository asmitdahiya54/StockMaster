from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required, roles_required

warehouses_bp = Blueprint("warehouses", __name__)


# GET: List all warehouses with stock summaries
@warehouses_bp.route("/", methods=["GET"])
@token_required
def get_warehouses():
    cursor = None

    try:
        search = request.args.get("search", "").strip()

        cursor = mysql.connection.cursor()

        query = """
            SELECT
                w.warehouse_id,
                w.warehouse_name,
                w.location,
                w.contact_number,
                COUNT(DISTINCT s.product_id) AS total_products,
                COALESCE(SUM(s.quantity), 0) AS total_stock_units,
                COALESCE(
                    SUM(s.quantity * p.unit_price), 0
                ) AS inventory_value
            FROM warehouses w
            LEFT JOIN stock s
                ON w.warehouse_id = s.warehouse_id
            LEFT JOIN products p
                ON s.product_id = p.product_id
        """

        params = []

        if search:
            query += """
                WHERE w.warehouse_name LIKE %s
                OR w.location LIKE %s
            """
            term = f"%{search}%"
            params.extend([term, term])

        query += """
            GROUP BY
                w.warehouse_id,
                w.warehouse_name,
                w.location,
                w.contact_number
            ORDER BY w.warehouse_id
        """

        cursor.execute(query, tuple(params))
        warehouses = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total": len(warehouses),
            "data": warehouses
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve warehouses"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET: Retrieve one warehouse
@warehouses_bp.route("/<int:warehouse_id>", methods=["GET"])
@token_required
def get_warehouse(warehouse_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                w.warehouse_id,
                w.warehouse_name,
                w.location,
                w.contact_number,
                w.created_at,
                COUNT(DISTINCT s.product_id) AS total_products,
                COALESCE(SUM(s.quantity), 0) AS total_stock_units,
                COALESCE(
                    SUM(s.quantity * p.unit_price), 0
                ) AS inventory_value
            FROM warehouses w
            LEFT JOIN stock s
                ON w.warehouse_id = s.warehouse_id
            LEFT JOIN products p
                ON s.product_id = p.product_id
            WHERE w.warehouse_id = %s
            GROUP BY
                w.warehouse_id,
                w.warehouse_name,
                w.location,
                w.contact_number,
                w.created_at
        """, (warehouse_id,))

        warehouse = cursor.fetchone()

        if not warehouse:
            return jsonify({
                "status": "error",
                "message": "Warehouse not found"
            }), 404

        return jsonify({
            "status": "success",
            "data": warehouse
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve warehouse"
        }), 500

    finally:
        if cursor:
            cursor.close()


# POST: Create warehouse
@warehouses_bp.route("/", methods=["POST"])
@roles_required("Admin", "Manager")
def create_warehouse():
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        name = data.get("warehouse_name")
        location = data.get("location")
        contact_number = data.get("contact_number")

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "status": "error",
                "message": "Warehouse name is required"
            }), 400

        if not isinstance(location, str) or not location.strip():
            return jsonify({
                "status": "error",
                "message": "Warehouse location is required"
            }), 400

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO warehouses
                (warehouse_name, location, contact_number)
            VALUES (%s, %s, %s)
        """, (
            name.strip(),
            location.strip(),
            contact_number
        ))

        warehouse_id = cursor.lastrowid
        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Warehouse created successfully",
            "warehouse_id": warehouse_id
        }), 201

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1062:
            return jsonify({
                "status": "error",
                "message": "Warehouse already exists"
            }), 409

        return jsonify({
            "status": "error",
            "message": "Unable to create warehouse"
        }), 500

    finally:
        if cursor:
            cursor.close()


# PUT: Update warehouse
@warehouses_bp.route("/<int:warehouse_id>", methods=["PUT"])
@roles_required("Admin", "Manager")
def update_warehouse(warehouse_id):
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        allowed_fields = {
            "warehouse_name",
            "location",
            "contact_number"
        }

        updates = {
            key: value
            for key, value in data.items()
            if key in allowed_fields
        }

        if not updates:
            return jsonify({
                "status": "error",
                "message": "No valid fields provided"
            }), 400

        for field in ("warehouse_name", "location"):
            if field in updates:
                value = updates[field]

                if not isinstance(value, str) or not value.strip():
                    return jsonify({
                        "status": "error",
                        "message": f"{field} cannot be empty"
                    }), 400

                updates[field] = value.strip()

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id = %s",
            (warehouse_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "status": "error",
                "message": "Warehouse not found"
            }), 404

        columns = ", ".join(
            f"{field} = %s" for field in updates
        )

        cursor.execute(
            f"UPDATE warehouses SET {columns} WHERE warehouse_id = %s",
            tuple(updates.values()) + (warehouse_id,)
        )

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Warehouse updated successfully"
        }), 200

    except Exception:
        mysql.connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Unable to update warehouse"
        }), 500

    finally:
        if cursor:
            cursor.close()


# DELETE: Delete warehouse (Admin only)
@warehouses_bp.route("/<int:warehouse_id>", methods=["DELETE"])
@roles_required("Admin")
def delete_warehouse(warehouse_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute(
            "DELETE FROM warehouses WHERE warehouse_id = %s",
            (warehouse_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Warehouse not found"
            }), 404

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Warehouse deleted successfully"
        }), 200

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1451:
            return jsonify({
                "status": "error",
                "message": "Cannot delete warehouse because existing records reference it"
            }), 409

        return jsonify({
            "status": "error",
            "message": "Unable to delete warehouse"
        }), 500

    finally:
        if cursor:
            cursor.close()
