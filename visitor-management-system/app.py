import datetime
from flask import Flask, render_template, redirect, url_for, session

from config import Config
from db import init_db
from auth_utils import login_required

from routes.auth import auth_bp
from routes.visitor import visitor_bp
from routes.host import host_bp
from routes.admin import admin_bp
from routes.checkin import checkin_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = datetime.timedelta(hours=8)

    init_db(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(visitor_bp)
    app.register_blueprint(host_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(checkin_bp)

    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard_redirect"))
        return redirect(url_for("visitor.register"))

    @app.route("/dashboard")
    @login_required
    def dashboard_redirect():
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        if role == "host":
            return redirect(url_for("host.dashboard"))
        if role == "security":
            return redirect(url_for("checkin.scan_page"))
        return redirect(url_for("visitor.register"))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403, message="You don't have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", code=500, message="Something went wrong on our end."), 500

    # Make the logged-in user's info available in every template
    @app.context_processor
    def inject_user():
        return {
            "logged_in": bool(session.get("user_id")),
            "current_role": session.get("role"),
            "current_full_name": session.get("full_name"),
        }

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
