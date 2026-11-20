from flask import Flask
from flask_cors import CORS
from .config import Config
from .extensions import mysql


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                r"http://localhost:\d+",
                r"http://127\.0\.0\.1:\d+"
            ]
        }
    }
)

    mysql.init_app(app)

    from .routes.health import health_bp
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.products import products_bp
    from .routes.categories import categories_bp
    from .routes.suppliers import suppliers_bp
    from .routes.warehouses import warehouses_bp
    from .routes.inventory import inventory_bp
    from .routes.purchase_orders import purchase_orders_bp
    from .routes.sales import sales_bp
    from .routes.transfers import transfers_bp
    from .routes.reports import reports_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(suppliers_bp, url_prefix="/api/suppliers")
    app.register_blueprint(warehouses_bp, url_prefix="/api/warehouses")
    app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
    app.register_blueprint(purchase_orders_bp, url_prefix="/api/purchase-orders")
    app.register_blueprint(sales_bp, url_prefix="/api/sales")
    app.register_blueprint(transfers_bp, url_prefix="/api/transfers")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    return app
