from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required, roles_required

products_bp = Blueprint("products", __name__)


# GET: List products with search, category filter and pagination
@products_bp.route("/", methods=["GET"])
@token_required
def get_products():
    cursor = None

    try:
        page = max(request.args.get("page", 1, type=int), 1)
        limit = request.args.get("limit", 10, type=int)

        if limit < 1 or limit > 100:
            return jsonify({
                "status": "error",
                "message": "Limit must be between 1 and 100"
            }), 400

        search = request.args.get("search", "").strip()
        category_id = request.args.get("category_id", type=int)

        conditions = []
        params = []

        if search:
            conditions.append(
                "(p.product_name LIKE %s OR p.sku LIKE %s)"
            )
            params.extend([f"%{search}%", f"%{search}%"])

        if category_id:
            conditions.append("p.category_id = %s")
            params.append(category_id)

        where_clause = (
            "WHERE " + " AND ".join(conditions)
            if conditions else ""
        )

        cursor = mysql.connection.cursor()

        cursor.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM products p
            {where_clause}
            """,
            tuple(params)
        )
        total = cursor.fetchone()["total"]

        offset = (page - 1) * limit

        cursor.execute(
            f"""
            SELECT
                p.product_id,
                p.sku,
                p.product_name,
                p.description,
                p.category_id,
                c.category_name,
                p.unit_price,
                p.reorder_level,
                p.created_at
            FROM products p
            LEFT JOIN categories c
                ON p.category_id = c.category_id
            {where_clause}
            ORDER BY p.product_id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [limit, offset])
        )

        products = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": products,
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
            "message": "Unable to retrieve products"
        }), 500

    finally:
        if cursor:
            cursor.close()


# GET: Retrieve one product
@products_bp.route("/<int:product_id>", methods=["GET"])
@token_required
def get_product(product_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                p.*,
                c.category_name
            FROM products p
            LEFT JOIN categories c
                ON p.category_id = c.category_id
            WHERE p.product_id = %s
        """, (product_id,))

        product = cursor.fetchone()

        if not product:
            return jsonify({
                "status": "error",
                "message": "Product not found"
            }), 404

        return jsonify({
            "status": "success",
            "data": product
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve product"
        }), 500

    finally:
        if cursor:
            cursor.close()


# POST: Add a new product
@products_bp.route("/", methods=["POST"])
@roles_required("Admin", "Manager")
def create_product():
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        sku = data.get("sku")
        name = data.get("product_name")
        category_id = data.get("category_id")
        price = data.get("unit_price")
        reorder_level = data.get("reorder_level", 10)
        description = data.get("description")

        if not isinstance(sku, str) or not sku.strip():
            return jsonify({
                "status": "error",
                "message": "SKU is required"
            }), 400

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "status": "error",
                "message": "Product name is required"
            }), 400

        if category_id is None or price is None:
            return jsonify({
                "status": "error",
                "message": "Category ID and unit price are required"
            }), 400

        try:
            category_id = int(category_id)
            price = float(price)
            reorder_level = int(reorder_level)

            if category_id < 1 or price < 0 or reorder_level < 0:
                raise ValueError()

        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Invalid category, price or reorder level"
            }), 400

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO products
                (sku, product_name, category_id, description,
                 unit_price, reorder_level)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            sku.strip(),
            name.strip(),
            category_id,
            description,
            price,
            reorder_level
        ))

        product_id = cursor.lastrowid
        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product created successfully",
            "product_id": product_id
        }), 201

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1062:
            return jsonify({
                "status": "error",
                "message": "A product with this SKU already exists"
            }), 409

        if getattr(error, "args", [None])[0] == 1452:
            return jsonify({
                "status": "error",
                "message": "The selected category does not exist"
            }), 400

        return jsonify({
            "status": "error",
            "message": "Unable to create product"
        }), 500

    finally:
        if cursor:
            cursor.close()


# PUT: Update an existing product
@products_bp.route("/<int:product_id>", methods=["PUT"])
@roles_required("Admin", "Manager")
def update_product(product_id):
    cursor = None

    try:
        data = request.get_json(silent=True) or {}

        allowed_fields = {
            "sku", "product_name", "category_id",
            "description", "unit_price", "reorder_level"
        }

        updates = {
            key: value
            for key, value in data.items()
            if key in allowed_fields
        }

        if not updates:
            return jsonify({
                "status": "error",
                "message": "No valid fields provided for update"
            }), 400

        if "sku" in updates and (
            not isinstance(updates["sku"], str)
            or not updates["sku"].strip()
        ):
            return jsonify({
                "status": "error",
                "message": "SKU cannot be empty"
            }), 400

        if "product_name" in updates and (
            not isinstance(updates["product_name"], str)
            or not updates["product_name"].strip()
        ):
            return jsonify({
                "status": "error",
                "message": "Product name cannot be empty"
            }), 400

        try:
            if "category_id" in updates:
                updates["category_id"] = int(updates["category_id"])
                if updates["category_id"] < 1:
                    raise ValueError()

            if "unit_price" in updates:
                updates["unit_price"] = float(updates["unit_price"])
                if updates["unit_price"] < 0:
                    raise ValueError()

            if "reorder_level" in updates:
                updates["reorder_level"] = int(updates["reorder_level"])
                if updates["reorder_level"] < 0:
                    raise ValueError()

        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": "Invalid numeric field"
            }), 400

        if "sku" in updates:
            updates["sku"] = updates["sku"].strip()

        if "product_name" in updates:
            updates["product_name"] = updates["product_name"].strip()

        cursor = mysql.connection.cursor()

        cursor.execute(
            "SELECT product_id FROM products WHERE product_id = %s",
            (product_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "status": "error",
                "message": "Product not found"
            }), 404

        columns = ", ".join(f"{key} = %s" for key in updates)

        cursor.execute(
            f"UPDATE products SET {columns} WHERE product_id = %s",
            tuple(updates.values()) + (product_id,)
        )

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product updated successfully"
        }), 200

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1062:
            return jsonify({
                "status": "error",
                "message": "SKU already exists"
            }), 409

        if getattr(error, "args", [None])[0] == 1452:
            return jsonify({
                "status": "error",
                "message": "The selected category does not exist"
            }), 400

        return jsonify({
            "status": "error",
            "message": "Unable to update product"
        }), 500

    finally:
        if cursor:
            cursor.close()


# DELETE: Delete a product (Admin only)
@products_bp.route("/<int:product_id>", methods=["DELETE"])
@roles_required("Admin")
def delete_product(product_id):
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute(
            "DELETE FROM products WHERE product_id = %s",
            (product_id,)
        )

        if cursor.rowcount == 0:
            return jsonify({
                "status": "error",
                "message": "Product not found"
            }), 404

        mysql.connection.commit()

        return jsonify({
            "status": "success",
            "message": "Product deleted successfully"
        }), 200

    except Exception as error:
        mysql.connection.rollback()

        if getattr(error, "args", [None])[0] == 1451:
            return jsonify({
                "status": "error",
                "message": "Cannot delete this product because it is referenced by existing records"
            }), 409

        return jsonify({
            "status": "error",
            "message": "Unable to delete product"
        }), 500

    finally:
        if cursor:
            cursor.close()
