
from flask import Blueprint, request, jsonify
from app.extensions import mysql
from app.utils.decorators import token_required

reports_bp = Blueprint("reports", __name__)


# 1. INVENTORY VALUATION
@reports_bp.route("/inventory-valuation", methods=["GET"])
@token_required
def inventory_valuation():
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                COUNT(DISTINCT p.product_id) AS total_products,
                COALESCE(SUM(s.quantity), 0) AS total_units,
                COALESCE(SUM(s.quantity * p.unit_price), 0) AS total_value
            FROM stock s
            JOIN products p ON s.product_id = p.product_id
        """)
        summary = cursor.fetchone()

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
            ORDER BY inventory_value DESC
        """)
        warehouses = cursor.fetchall()

        cursor.execute("""
            SELECT
                p.product_id,
                p.sku,
                p.product_name,
                COALESCE(SUM(s.quantity), 0) AS total_quantity,
                p.unit_price,
                COALESCE(SUM(s.quantity * p.unit_price), 0) AS inventory_value
            FROM products p
            LEFT JOIN stock s ON p.product_id = s.product_id
            GROUP BY p.product_id, p.sku, p.product_name, p.unit_price
            ORDER BY inventory_value DESC
        """)
        products = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": {
                "summary": summary,
                "warehouse_breakdown": warehouses,
                "products": products
            }
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to generate inventory valuation report"
        }), 500
    finally:
        if cursor:
            cursor.close()


# 2. LOW STOCK REPORT
@reports_bp.route("/low-stock", methods=["GET"])
@token_required
def low_stock_report():
    cursor = None
    try:
        warehouse_id = request.args.get("warehouse_id", type=int)
        cursor = mysql.connection.cursor()

        query = """
            SELECT
                p.product_id,
                p.sku,
                p.product_name,
                c.category_name,
                w.warehouse_id,
                w.warehouse_name,
                COALESCE(s.quantity, 0) AS available_quantity,
                p.reorder_level,
                GREATEST(
                    p.reorder_level - COALESCE(s.quantity, 0), 0
                ) AS shortage
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            CROSS JOIN warehouses w
            LEFT JOIN stock s
                ON p.product_id = s.product_id
                AND w.warehouse_id = s.warehouse_id
            WHERE COALESCE(s.quantity, 0) <= p.reorder_level
        """

        params = []
        if warehouse_id is not None:
            query += " AND w.warehouse_id = %s"
            params.append(warehouse_id)

        query += " ORDER BY shortage DESC, p.product_name"

        cursor.execute(query, tuple(params))
        records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total_records": len(records),
            "data": records
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to generate low-stock report"
        }), 500
    finally:
        if cursor:
            cursor.close()


# 3. SALES ANALYTICS
@reports_bp.route("/sales-summary", methods=["GET"])
@token_required
def sales_summary():
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                COUNT(DISTINCT s.sale_id) AS total_orders,
                COUNT(DISTINCT CASE
                    WHEN s.status = 'Completed' THEN s.sale_id
                END) AS completed_orders,
                COUNT(DISTINCT CASE
                    WHEN s.status = 'Pending' THEN s.sale_id
                END) AS pending_orders,
                COALESCE(SUM(
                    CASE WHEN s.status = 'Completed'
                    THEN si.quantity * si.unit_price ELSE 0 END
                ), 0) AS completed_revenue,
                COALESCE(SUM(
                    CASE WHEN s.status = 'Pending'
                    THEN si.quantity * si.unit_price ELSE 0 END
                ), 0) AS pending_order_value
            FROM sales s
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        """)
        summary = cursor.fetchone()

        cursor.execute("""
            SELECT
                s.sale_id,
                c.customer_name,
                w.warehouse_name,
                s.sale_date,
                s.status,
                COALESCE(SUM(si.quantity * si.unit_price), 0) AS sale_total
            FROM sales s
            JOIN customers c ON s.customer_id = c.customer_id
            JOIN warehouses w ON s.warehouse_id = w.warehouse_id
            LEFT JOIN sale_items si ON s.sale_id = si.sale_id
            GROUP BY
                s.sale_id, c.customer_name,
                w.warehouse_name, s.sale_date, s.status
            ORDER BY s.sale_date DESC
            LIMIT 10
        """)
        recent_sales = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": {
                "summary": summary,
                "recent_sales": recent_sales
            }
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to generate sales summary"
        }), 500
    finally:
        if cursor:
            cursor.close()


# 4. MONTHLY SALES TRENDS
@reports_bp.route("/monthly-sales", methods=["GET"])
@token_required
def monthly_sales():
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                DATE_FORMAT(s.sale_date, '%Y-%m') AS month,
                COUNT(DISTINCT s.sale_id) AS total_orders,
                SUM(si.quantity) AS units_sold,
                COALESCE(SUM(si.quantity * si.unit_price), 0) AS revenue
            FROM sales s
            JOIN sale_items si ON s.sale_id = si.sale_id
            WHERE s.status = 'Completed'
            GROUP BY DATE_FORMAT(s.sale_date, '%Y-%m')
            ORDER BY month ASC
        """)

        records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": records
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to generate monthly sales report"
        }), 500
    finally:
        if cursor:
            cursor.close()


# 5. FAST AND SLOW MOVING PRODUCTS
@reports_bp.route("/product-performance", methods=["GET"])
@token_required
def product_performance():
    cursor = None
    try:
        limit = min(max(request.args.get("limit", 10, type=int), 1), 50)
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                p.product_id,
                p.sku,
                p.product_name,
                COALESCE(SUM(
                    CASE WHEN s.status = 'Completed'
                    THEN si.quantity ELSE 0 END
                ), 0) AS units_sold,
                COALESCE(SUM(
                    CASE WHEN s.status = 'Completed'
                    THEN si.quantity * si.unit_price ELSE 0 END
                ), 0) AS sales_revenue
            FROM products p
            LEFT JOIN sale_items si ON p.product_id = si.product_id
            LEFT JOIN sales s ON si.sale_id = s.sale_id
            GROUP BY p.product_id, p.sku, p.product_name
            ORDER BY units_sold DESC, p.product_name
        """)

        products = cursor.fetchall()

        fast_moving = products[:limit]
        slow_moving = list(reversed(products[-limit:]))

        return jsonify({
            "status": "success",
            "data": {
                "fast_moving_products": fast_moving,
                "slow_moving_products": slow_moving
            }
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to generate product performance report"
        }), 500
    finally:
        if cursor:
            cursor.close()


# 6. SUPPLIER PERFORMANCE
@reports_bp.route("/supplier-performance", methods=["GET"])
@token_required
def supplier_performance():
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                sp.supplier_id,
                sp.supplier_name,
                COUNT(DISTINCT po.purchase_order_id) AS total_orders,
                COUNT(DISTINCT CASE
                    WHEN po.status = 'Received'
                    THEN po.purchase_order_id
                END) AS received_orders,
                COUNT(DISTINCT CASE
                    WHEN po.status = 'Pending'
                    THEN po.purchase_order_id
                END) AS pending_orders,
                COALESCE(SUM(
                    CASE WHEN po.status = 'Received'
                    THEN poi.quantity * poi.unit_cost ELSE 0 END
                ), 0) AS received_purchase_value,
                COALESCE(SUM(
                    CASE WHEN po.status = 'Pending'
                    THEN poi.quantity * poi.unit_cost ELSE 0 END
                ), 0) AS pending_purchase_value
            FROM suppliers sp
            LEFT JOIN purchase_orders po
                ON sp.supplier_id = po.supplier_id
            LEFT JOIN purchase_order_items poi
                ON po.purchase_order_id = poi.purchase_order_id
            GROUP BY sp.supplier_id, sp.supplier_name
            ORDER BY received_purchase_value DESC
        """)

        records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": records
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to generate supplier performance report"
        }), 500
    finally:
        if cursor:
            cursor.close()


# 7. WAREHOUSE PERFORMANCE
@reports_bp.route("/warehouse-performance", methods=["GET"])
@token_required
def warehouse_performance():
    cursor = None
    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                w.warehouse_id,
                w.warehouse_name,
                COALESCE(stock_data.total_products, 0) AS total_products,
                COALESCE(stock_data.total_units, 0) AS total_units,
                COALESCE(stock_data.inventory_value, 0) AS inventory_value,
                COALESCE(sales_data.total_orders, 0) AS total_orders,
                COALESCE(sales_data.completed_revenue, 0) AS completed_revenue
            FROM warehouses w
            LEFT JOIN (
                SELECT
                    st.warehouse_id,
                    COUNT(DISTINCT st.product_id) AS total_products,
                    SUM(st.quantity) AS total_units,
                    SUM(st.quantity * p.unit_price) AS inventory_value
                FROM stock st
                JOIN products p ON st.product_id = p.product_id
                GROUP BY st.warehouse_id
            ) stock_data ON w.warehouse_id = stock_data.warehouse_id
            LEFT JOIN (
                SELECT
                    warehouse_id,
                    COUNT(*) AS total_orders,
                    SUM(CASE
                        WHEN status = 'Completed' THEN 1 ELSE 0
                    END) AS completed_orders,
                    SUM(CASE
                        WHEN status = 'Completed'
                        THEN sale_totals.sale_amount ELSE 0
                    END) AS completed_revenue
                FROM (
                    SELECT
                        s.sale_id,
                        s.warehouse_id,
                        s.status,
                        COALESCE(SUM(
                            si.quantity * si.unit_price
                        ), 0) AS sale_amount
                    FROM sales s
                    LEFT JOIN sale_items si ON s.sale_id = si.sale_id
                    GROUP BY s.sale_id, s.warehouse_id, s.status
                ) sale_totals
                GROUP BY warehouse_id
            ) sales_data ON w.warehouse_id = sales_data.warehouse_id
            ORDER BY inventory_value DESC
        """)

        records = cursor.fetchall()

        return jsonify({
            "status": "success",
            "data": records
        }), 200

    except Exception:
        return jsonify({
            "status": "error",
            "message": "Unable to generate warehouse performance report"
        }), 500
    finally:
        if cursor:
            cursor.close()
