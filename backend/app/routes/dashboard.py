from flask import Blueprint, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/summary", methods=["GET"])
@token_required
def dashboard_summary():
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM products) AS total_products,
                (SELECT COUNT(*) FROM warehouses) AS total_warehouses,
                (SELECT COUNT(*) FROM suppliers) AS total_suppliers,
                (SELECT COUNT(*) FROM customers) AS total_customers,
                (SELECT COALESCE(SUM(quantity), 0) FROM stock) AS total_stock_units,
                (
                    SELECT COALESCE(SUM(s.quantity * p.unit_price), 0)
                    FROM stock s
                    JOIN products p ON s.product_id = p.product_id
                ) AS inventory_value,
                (
                    SELECT COUNT(DISTINCT s.product_id)
                    FROM stock s
                    JOIN products p ON s.product_id = p.product_id
                    WHERE s.quantity <= p.reorder_level
                ) AS low_stock_products,
                (
                    SELECT COALESCE(SUM(si.quantity * si.unit_price), 0)
                    FROM sale_items si
                    JOIN sales sa ON si.sale_id = sa.sale_id
                    WHERE sa.status = 'Completed'
                ) AS completed_sales_value
        """)

        summary = cursor.fetchone()

        return jsonify({
            "status": "success",
            "message": "Dashboard summary retrieved successfully",
            "data": summary
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve dashboard summary"
        }), 500

    finally:
        if cursor:
            cursor.close()


@dashboard_bp.route("/warehouse-stock", methods=["GET"])
@token_required
def warehouse_stock():
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                w.warehouse_id,
                w.warehouse_name,
                COALESCE(SUM(s.quantity), 0) AS total_units,
                COALESCE(SUM(s.quantity * p.unit_price), 0) AS inventory_value
            FROM warehouses w
            LEFT JOIN stock s ON w.warehouse_id = s.warehouse_id
            LEFT JOIN products p ON s.product_id = p.product_id
            GROUP BY w.warehouse_id, w.warehouse_name
            ORDER BY total_units DESC
        """)

        warehouses = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": warehouses
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve warehouse stock"
        }), 500

    finally:
        if cursor:
            cursor.close()


@dashboard_bp.route("/low-stock", methods=["GET"])
@token_required
def dashboard_low_stock():
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                p.product_id,
                p.product_name,
                p.sku,
                w.warehouse_name,
                s.quantity,
                p.reorder_level
            FROM stock s
            JOIN products p ON s.product_id = p.product_id
            JOIN warehouses w ON s.warehouse_id = w.warehouse_id
            WHERE s.quantity <= p.reorder_level
            ORDER BY s.quantity ASC
        """)

        products = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": products
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve low-stock products"
        }), 500

    finally:
        if cursor:
            cursor.close()
