import jwt
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import check_password_hash
from app.extensions import mysql
from app.utils.decorators import token_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password are required"
        }), 400

    cursor = None

    try:
        cursor = mysql.connection.cursor()

        cursor.execute("""
            SELECT
                u.user_id,
                u.full_name,
                u.email,
                u.password_hash,
                u.is_active,
                r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            WHERE u.email = %s
            LIMIT 1
        """, (email,))

        user = cursor.fetchone()

        if not user or not user["is_active"]:
            return jsonify({
                "status": "error",
                "message": "Invalid email or password"
            }), 401

        if not check_password_hash(user["password_hash"], password):
            return jsonify({
                "status": "error",
                "message": "Invalid email or password"
            }), 401

        now = datetime.now(timezone.utc)

        token = jwt.encode({
            "user_id": user["user_id"],
            "email": user["email"],
            "role": user["role_name"],
            "iat": now,
            "exp": now + timedelta(hours=8)
        }, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "token": token,
            "user": {
                "user_id": user["user_id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "role": user["role_name"]
            }
        }), 200

    except Exception:
        current_app.logger.exception("Login failed")
        return jsonify({
            "status": "error",
            "message": "Unable to process login"
        }), 500

    finally:
        if cursor:
            cursor.close()


@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user():
    return jsonify({
        "status": "success",
        "user": request.current_user
    }), 200
