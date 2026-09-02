"""
auth_utils.py
-------------
Session-based authentication helpers and role-based access control (RBAC)
decorators, shared across every blueprint.

Roles used in this system:
    admin     - full access: manage users, view analytics, manage all visitors
    host      - employee who receives visitors: approve/reject, view own visitors
    security  - front-desk / gate staff: check-in & check-out visitors via QR
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request, abort
from bson.objectid import ObjectId

from db import get_db


def current_user():
    """Return the logged-in user's document, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    db = get_db()
    return db.users.find_one({"_id": ObjectId(user_id)})


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    """Restrict a view to one or more roles, e.g. @roles_required('admin', 'host')."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if session.get("role") not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator
