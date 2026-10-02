"""
Fieldhouse — Equipment Operations
Main Flask application entry point.

Run with:  python app.py
"""

from flask import Flask, render_template, redirect, url_for, session
import pymysql

from config import Config
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.equipment import equipment_bp
from routes.categories import categories_bp
from routes.members import members_bp
from routes.issues import issues_bp
from routes.returns import returns_bp
from routes.maintenance import maintenance_bp
from routes.damage import damage_bp
from routes.reports import reports_bp
from routes.team import team_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints (modular route files)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(issues_bp)
    app.register_blueprint(returns_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(damage_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(team_bp)

    # -----------------------------------------------------
    # Root route
    # -----------------------------------------------------
    @app.route("/")
    def home():
        if "user_id" in session:
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    # -----------------------------------------------------
    # Make current session info + the sidebar status ticker
    # available in every template
    # -----------------------------------------------------
    @app.context_processor
    def inject_user():
        ticker = None
        if "user_id" in session:
            try:
                from database import get_db_connection
                conn = get_db_connection()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT COUNT(*) AS c FROM equipment_issues WHERE return_status IN ('Issued','Partially Returned')"
                        )
                        issued = cursor.fetchone()["c"]
                        cursor.execute(
                            """SELECT COUNT(*) AS c FROM equipment_issues
                               WHERE expected_return_date < CURDATE()
                               AND return_status IN ('Issued','Partially Returned')"""
                        )
                        overdue = cursor.fetchone()["c"]
                        cursor.execute(
                            "SELECT COUNT(*) AS c FROM maintenance_records WHERE status IN ('Pending','In Progress')"
                        )
                        in_repair = cursor.fetchone()["c"]
                        cursor.execute(
                            "SELECT COUNT(*) AS c FROM users WHERE is_active = 0"
                        )
                        pending_users = cursor.fetchone()["c"]
                    ticker = {
                        "issued": issued,
                        "overdue": overdue,
                        "in_repair": in_repair,
                        "pending_users": pending_users,
                    }
                finally:
                    conn.close()
            except Exception:
                ticker = None

        return {
            "current_user": session.get("full_name"),
            "current_role": session.get("role"),
            "ticker": ticker,
        }

    # -----------------------------------------------------
    # Error handlers
    # -----------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(pymysql.MySQLError)
    def db_error(e):
        return render_template("errors/500.html", db_error=True), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
