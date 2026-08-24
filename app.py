from flask import Flask, g, redirect, url_for

from config import Config
from core import auth as core_auth
from core import db as core_db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    core_db.init_app(app)
    core_auth.init_app(app)

    from blueprints.auth import bp as auth_bp
    from blueprints.dev_portal import bp as dev_portal_bp
    from blueprints.marketing import bp as marketing_bp
    from blueprints.qc_portal import bp as qc_portal_bp
    from blueprints.sales import bp as sales_bp
    from blueprints.super_admin import bp as super_admin_bp
    from blueprints.tenant_app import bp as tenant_app_bp
    from mock_integrations import bp as mock_integrations_bp
    from projects.webhook_api import bp as webhook_api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(super_admin_bp)
    app.register_blueprint(dev_portal_bp)
    app.register_blueprint(qc_portal_bp)
    app.register_blueprint(marketing_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(tenant_app_bp)
    app.register_blueprint(mock_integrations_bp)
    app.register_blueprint(webhook_api_bp)

    from core.cli_api import bp as cli_api_bp

    app.register_blueprint(cli_api_bp)

    import core.api_auth as api_auth
    import crm.api as crm_api

    crm_api.register(app)
    api_auth.register(app)

    @app.route("/")
    def root():
        from blueprints.auth.routes import ROLE_HOME

        if g.user:
            home = ROLE_HOME.get(g.user["role"])
            if home:
                return redirect(home(g.user))
        return redirect(url_for("auth.login"))

    @app.context_processor
    def inject_notifications():
        if g.get("user"):
            from crm.helpers import list_notifications, unread_count

            return {
                "nav_notifications": list_notifications(g.user["id"]),
                "nav_unread_count": unread_count(g.user["id"]),
            }
        return {"nav_notifications": [], "nav_unread_count": 0}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
