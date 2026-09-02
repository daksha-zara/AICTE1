import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db
from auth_utils import roles_required, current_user

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard_redirect"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.users.find_one({"username": username})

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        if not user.get("is_active", True):
            flash("Your account has been disabled. Contact the administrator.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"] = str(user["_id"])
        session["role"] = user["role"]
        session["full_name"] = user["full_name"]
        session.permanent = True

        flash(f"Welcome back, {user['full_name']}!", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("dashboard_redirect"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Self-registration for Host and Security staff.
    Admins can only be created by an existing admin via /admin/users."""
    if session.get("user_id"):
        return redirect(url_for("dashboard_redirect"))

    form = {}
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()
        role = request.form.get("role", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Preserve form data for re-render on error
        form = {
            "full_name": full_name, "username": username,
            "email": email, "department": department, "role": role,
        }

        # Validation
        if role not in ("host", "security"):
            flash("Please select a valid role (Host or Security).", "error")
            return render_template("register.html", form=form)

        if not all([full_name, username, email, password]):
            flash("All required fields must be filled in.", "error")
            return render_template("register.html", form=form)

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html", form=form)

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html", form=form)

        db = get_db()
        if db.users.find_one({"$or": [{"username": username}, {"email": email}]}):
            flash("A user with that username or email already exists.", "error")
            return render_template("register.html", form=form)

        db.users.insert_one({
            "username": username,
            "email": email,
            "full_name": full_name,
            "department": department,
            "role": role,
            "password_hash": generate_password_hash(password),
            "is_active": True,
            "created_at": datetime.datetime.utcnow(),
        })

        flash(f"Account created! Welcome, {full_name}. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


# Admin-only: manage host / security / admin accounts
# ---------------------------------------------------------------------------
@auth_bp.route("/admin/users", methods=["GET", "POST"])
@roles_required("admin")
def manage_users():
    db = get_db()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        department = request.form.get("department", "").strip()
        role = request.form.get("role", "host")
        password = request.form.get("password", "")

        if role not in ("admin", "host", "security"):
            flash("Invalid role selected.", "error")
            return redirect(url_for("auth.manage_users"))

        if db.users.find_one({"$or": [{"username": username}, {"email": email}]}):
            flash("A user with that username or email already exists.", "error")
            return redirect(url_for("auth.manage_users"))

        db.users.insert_one({
            "username": username,
            "email": email,
            "full_name": full_name,
            "department": department,
            "role": role,
            "password_hash": generate_password_hash(password),
            "is_active": True,
            "created_at": datetime.datetime.utcnow(),
        })
        flash(f"User '{username}' created successfully as {role}.", "success")
        return redirect(url_for("auth.manage_users"))

    users = list(db.users.find().sort("created_at", -1))
    return render_template("admin_users.html", users=users)


@auth_bp.route("/admin/users/<user_id>/toggle", methods=["POST"])
@roles_required("admin")
def toggle_user(user_id):
    from bson.objectid import ObjectId
    db = get_db()
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("auth.manage_users"))

    if str(user["_id"]) == session.get("user_id"):
        flash("You cannot disable your own account.", "error")
        return redirect(url_for("auth.manage_users"))

    db.users.update_one({"_id": user["_id"]}, {"$set": {"is_active": not user.get("is_active", True)}})
    flash("User status updated.", "success")
    return redirect(url_for("auth.manage_users"))


@auth_bp.route("/profile")
@roles_required("admin", "host", "security")
def profile():
    return render_template("profile.html", user=current_user())
