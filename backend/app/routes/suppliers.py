from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required, roles_required

suppliers_bp = Blueprint("suppliers", __name__)

ALLOWED_FIELDS = {
    "supplier_name",
    "contact_person",
    "email",
    "phone",
    "address"
}


# GET: List suppliers with search and pagination
@suppliers_bp.route("/", methods=["GET"])
@token_required
def get_suppliers():
    cursor = None

    try:
        page = max(request.args.get("page", 1, type=int), 1)
        limit = request.args.get("limit", 10, type=int)

        if not 1 <= limit <= 100:
            return jsonify({
                "status": "error",
                "message": "Limit must be between 1 and 100"
            }), 400

        search = request.args.get("search", "").strip()

        where_clause = ""
        params = []

        if search:
            where_clause = """
                WHERE supplier_name LIKE %s
                OR contact_person LIKE %s
                OR email LIKE %s
            """
            term = f"%{search}%"
            params = [term, term, term]

        cursor = mysql.connection.cursor()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM suppliers
            {where_clause}
            """,
            tuple(params)
        )

        total = cursor.fetchone()["total"]
        offset = (page - 1) * limit

        cursor.execute(
            f"""
            SELECT
                supplier_id,
                supplier_name,
                contact_person,
                email,
                phone,
                address
            FROM suppliers
            {where_clause}
            ORDER BY supplier_id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )

        suppliers = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": suppliers,
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
            "message": "Unable to retrieve suppliers"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET: Retrieve one supplier
@suppliers_bp.route("/<int:supplier_id>", methods=["GET"])
@token_required
def get_supplier(supplier_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                supplier_id,
                supplier_name,
                contact_person,
                email,
                phone,
                address
            FROM suppliers
            WHERE supplier_id = %s
        """, (supplier_id,))

        supplier = cursor.fetchone()

        if not supplier:
            return jsonify({
                "status": "error",
                "message": "Supplier not found"
            }), 404

        return jsonify({
            "status": "success",
            "data": supplier
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve supplier"
        }), 500

    finally:
        if cursor:
            cursor.close()


# POST: Create supplier
@suppliers_bp.route("/", methods=["POST"])
@roles_required("Admin", "Manager")
def create_supplier():
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        name = data.get("supplier_name")

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "status": "error",
                "message": "Supplier name is required"
            }), 400

        contact_person = data.get("contact_person")
        email = data.get("email")
        phone = data.get("phone")
        address = data.get("address")

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO suppliers
                (supplier_name, contact_person, email, phone, address)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            name.strip(),
            contact_person,
            email,
            phone,
            address
        ))

        supplier_id = cursor.lastrowid
        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Supplier created successfully",
            "supplier_id": supplier_id
        }), 201

    except Exception:
        mysql.connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Unable to create supplier"
        }), 500

    finally:
        if cursor:
            cursor.close()


# PUT: Update supplier
@suppliers_bp.route("/<int:supplier_id>", methods=["PUT"])
@roles_required("Admin", "Manager")
def update_supplier(supplier_id):
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        updates = {
            key: value
            for key, value in data.items()
            if key in ALLOWED_FIELDS
        }

        if not updates:
            return jsonify({
                "status": "error",
                "message": "No valid fields provided"
            }), 400

        if "supplier_name" in updates:
            name = updates["supplier_name"]

            if not isinstance(name, str) or not name.strip():
                return jsonify({
                    "status": "error",
                    "message": "Supplier name cannot be empty"
                }), 400

            updates["supplier_name"] = name.strip()

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT supplier_id FROM suppliers WHERE supplier_id = %s",
            (supplier_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "status": "error",
                "message": "Supplier not found"
            }), 404

        columns = ", ".join(
            f"{field} = %s" for field in updates
        )

        cursor.execute(
            f"UPDATE suppliers SET {columns} WHERE supplier_id = %s",
            tuple(updates.values()) + (supplier_id,)
        )

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Supplier updated successfully"
        }), 200

    except Exception:
        mysql.connection.rollback()

        return jsonify({
            "status": "error",
            "message": "Unable to update supplier"
        }), 500

    finally:
        if cursor:
            cursor.close()


# DELETE: Delete supplier (Admin only)
@suppliers_bp.route("/<int:supplier_id>", methods=["DELETE"])
@roles_required("Admin")
def delete_supplier(supplier_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute(
            "DELETE FROM suppliers WHERE supplier_id = %s",
            (supplier_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Supplier not found"
            }), 404

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Supplier deleted successfully"
        }), 200

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1451:
            return jsonify({
                "status": "error",
                "message": "Cannot delete supplier because purchase orders reference it"
            }), 409

        return jsonify({
            "status": "error",
            "message": "Unable to delete supplier"
        }), 500

    finally:
        if cursor:
            cursor.close()
