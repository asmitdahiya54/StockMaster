from flask import Blueprint, jsonify, current_app
from app.extensions import mysql

health_bp = Blueprint("health", __name__)

@health_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "success",
        "message": "StockMaster API is running"
    }), 200

@health_bp.route("/db-test", methods=["GET"])
def database_test():
    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                DATABASE() AS database_name,
                (SELECT COUNT(*) FROM products) AS total_products,
                (SELECT COUNT(*) FROM warehouses) AS total_warehouses
        """)

        result = cursor.fetchone()

        return jsonify({
            "status": "success",
            "message": "MySQL connection successful",
            "data": result
        }), 200

    except Exception as error:
        current_app.logger.exception("MySQL connection test failed")

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()
