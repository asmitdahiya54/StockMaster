from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required, roles_required

categories_bp = Blueprint("categories", __name__)


# GET: Retrieve all categories
@categories_bp.route("/", methods=["GET"])
@token_required
def get_categories():
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                c.category_id,
                c.category_name,
                c.description,
                COUNT(p.product_id) AS total_products
            FROM categories c
            LEFT JOIN products p
                ON c.category_id = p.category_id
            GROUP BY
                c.category_id,
                c.category_name,
                c.description
            ORDER BY c.category_id
        """)

        categories = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total": len(categories),
            "data": categories
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve categories"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET: Retrieve one category
@categories_bp.route("/<int:category_id>", methods=["GET"])
@token_required
def get_category(category_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                c.category_id,
                c.category_name,
                c.description,
                COUNT(p.product_id) AS total_products
            FROM categories c
            LEFT JOIN products p
                ON c.category_id = p.category_id
            WHERE c.category_id = %s
            GROUP BY
                c.category_id,
                c.category_name,
                c.description
        """, (category_id,))

        category = cursor.fetchone()

        if not category:
            return jsonify({
                "status": "error",
                "message": "Category not found"
            }), 404

        return jsonify({
            "status": "success",
            "data": category
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve category"
        }), 500

    finally:
        if cursor:
            cursor.close()


# POST: Create a category
@categories_bp.route("/", methods=["POST"])
@roles_required("Admin", "Manager")
def create_category():
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        name = data.get("category_name")
        description = data.get("description")

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "status": "error",
                "message": "Category name is required"
            }), 400

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO categories (category_name, description)
            VALUES (%s, %s)
        """, (name.strip(), description))

        category_id = cursor.lastrowid
        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Category created successfully",
            "category_id": category_id
        }), 201

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1062:
            return jsonify({
                "status": "error",
                "message": "Category already exists"
            }), 409

        return jsonify({
            "status": "error",
            "message": "Unable to create category"
        }), 500

    finally:
        if cursor:
            cursor.close()


# PUT: Update a category
@categories_bp.route("/<int:category_id>", methods=["PUT"])
@roles_required("Admin", "Manager")
def update_category(category_id):
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        updates = {}

        if "category_name" in data:
            name = data["category_name"]

            if not isinstance(name, str) or not name.strip():
                return jsonify({
                    "status": "error",
                    "message": "Category name cannot be empty"
                }), 400

            updates["category_name"] = name.strip()

        if "description" in data:
            updates["description"] = data["description"]

        if not updates:
            return jsonify({
                "status": "error",
                "message": "No valid fields provided"
            }), 400

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT category_id FROM categories WHERE category_id = %s",
            (category_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "status": "error",
                "message": "Category not found"
            }), 404

        columns = ", ".join(
            f"{field} = %s" for field in updates
        )

        cursor.execute(
            f"UPDATE categories SET {columns} WHERE category_id = %s",
            tuple(updates.values()) + (category_id,)
        )

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Category updated successfully"
        }), 200

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1062:
            return jsonify({
                "status": "error",
                "message": "Category name already exists"
            }), 409

        return jsonify({
            "status": "error",
            "message": "Unable to update category"
        }), 500

    finally:
        if cursor:
            cursor.close()


# DELETE: Delete a category (Admin only)
@categories_bp.route("/<int:category_id>", methods=["DELETE"])
@roles_required("Admin")
def delete_category(category_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute(
            "DELETE FROM categories WHERE category_id = %s",
            (category_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Category not found"
            }), 404

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Category deleted successfully"
        }), 200

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1451:
            return jsonify({
                "status": "error",
                "message": "Cannot delete this category because products are linked to it"
            }), 409

        return jsonify({
            "status": "error",
            "message": "Unable to delete category"
        }), 500

    finally:
        if cursor:
            cursor.close()
