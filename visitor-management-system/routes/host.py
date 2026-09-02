import datetime
from bson.objectid import ObjectId
from flask import Blueprint, render_template, redirect, url_for, flash, session, jsonify

from db import get_db
from auth_utils import roles_required

host_bp = Blueprint("host", __name__)


@host_bp.route("/host/dashboard")
@roles_required("host")
def dashboard():
    db = get_db()
    host_id = session["user_id"]

    pending = list(db.visitors.find({"host_id": host_id, "status": "pending"}).sort("created_at", -1))
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays_visitors = list(db.visitors.find({
        "host_id": host_id,
        "created_at": {"$gte": today_start},
    }).sort("created_at", -1))

    notifications = list(db.notifications.find({"host_id": host_id}).sort("created_at", -1).limit(15))

    return render_template(
        "host_dashboard.html",
        pending=pending,
        todays_visitors=todays_visitors,
        notifications=notifications,
    )


@host_bp.route("/host/visitor/<visitor_id>/approve", methods=["POST"])
@roles_required("host")
def approve(visitor_id):
    db = get_db()
    visitor = db.visitors.find_one({"_id": ObjectId(visitor_id), "host_id": session["user_id"]})
    if not visitor:
        flash("Visitor not found.", "error")
        return redirect(url_for("host.dashboard"))

    db.visitors.update_one({"_id": visitor["_id"]}, {"$set": {"status": "approved"}})
    flash(f"{visitor['full_name']} approved. They can now check in at the gate.", "success")
    return redirect(url_for("host.dashboard"))


@host_bp.route("/host/visitor/<visitor_id>/reject", methods=["POST"])
@roles_required("host")
def reject(visitor_id):
    db = get_db()
    visitor = db.visitors.find_one({"_id": ObjectId(visitor_id), "host_id": session["user_id"]})
    if not visitor:
        flash("Visitor not found.", "error")
        return redirect(url_for("host.dashboard"))

    db.visitors.update_one({"_id": visitor["_id"]}, {"$set": {"status": "rejected"}})
    flash(f"{visitor['full_name']} was rejected.", "success")
    return redirect(url_for("host.dashboard"))


@host_bp.route("/host/notifications/mark-read", methods=["POST"])
@roles_required("host")
def mark_notifications_read():
    db = get_db()
    db.notifications.update_many({"host_id": session["user_id"], "is_read": False}, {"$set": {"is_read": True}})
    return jsonify({"ok": True})


@host_bp.route("/host/notifications/unread-count")
@roles_required("host")
def unread_count():
    db = get_db()
    count = db.notifications.count_documents({"host_id": session["user_id"], "is_read": False})
    return jsonify({"count": count})
