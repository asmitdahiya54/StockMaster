import jwt
from functools import wraps
from flask import request, jsonify, current_app


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({
                "status": "error",
                "message": "Authentication token required"
            }), 401

        token = auth_header.split(" ", 1)[1]

        try:
            payload = jwt.decode(
                token,
                current_app.config["JWT_SECRET_KEY"],
                algorithms=["HS256"]
            )

            request.current_user = payload

        except jwt.ExpiredSignatureError:
            return jsonify({
                "status": "error",
                "message": "Token has expired"
            }), 401

        except jwt.InvalidTokenError:
            return jsonify({
                "status": "error",
                "message": "Invalid authentication token"
            }), 401

        return f(*args, **kwargs)

    return decorated


def roles_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            user_role = request.current_user.get("role")

            if user_role not in allowed_roles:
                return jsonify({
                    "status": "error",
                    "message": "You do not have permission"
                }), 403

            return f(*args, **kwargs)

        return decorated
    return decorator
