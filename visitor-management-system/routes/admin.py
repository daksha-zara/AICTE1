import datetime
from flask import Blueprint, render_template, jsonify, request

from db import get_db
from auth_utils import roles_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin/dashboard")
@roles_required("admin")
def dashboard():
    db = get_db()

    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_visitors = db.visitors.count_documents({})
    today_visitors = db.visitors.count_documents({"created_at": {"$gte": today_start}})
    currently_in = db.visitors.count_documents({"status": "checked_in"})
    pending_approval = db.visitors.count_documents({"status": "pending"})
    total_hosts = db.users.count_documents({"role": "host", "is_active": True})

    recent_visitors = list(db.visitors.find().sort("created_at", -1).limit(10))

    stats = {
        "total_visitors": total_visitors,
        "today_visitors": today_visitors,
        "currently_in": currently_in,
        "pending_approval": pending_approval,
        "total_hosts": total_hosts,
    }

    return render_template("admin_dashboard.html", stats=stats, recent_visitors=recent_visitors)


@admin_bp.route("/admin/visitors")
@roles_required("admin")
def all_visitors():
    db = get_db()
    status_filter = request.args.get("status")
    query = {}
    if status_filter and status_filter != "all":
        query["status"] = status_filter
    visitors = list(db.visitors.find(query).sort("created_at", -1).limit(200))
    return render_template("admin_visitors.html", visitors=visitors, status_filter=status_filter or "all")


@admin_bp.route("/admin/analytics/data")
@roles_required("admin")
def analytics_data():
    """JSON feed consumed by Chart.js on the admin dashboard
    (module: Admin Dashboard & Visitor Analytics)."""
    db = get_db()

    # Visitors per day for the last 7 days
    today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    days, counts = [], []
    for i in range(6, -1, -1):
        day_start = today - datetime.timedelta(days=i)
        day_end = day_start + datetime.timedelta(days=1)
        c = db.visitors.count_documents({"created_at": {"$gte": day_start, "$lt": day_end}})
        days.append(day_start.strftime("%d %b"))
        counts.append(c)

    # Status breakdown
    status_labels = ["pending", "approved", "rejected", "checked_in", "checked_out"]
    status_counts = [db.visitors.count_documents({"status": s}) for s in status_labels]

    # Visitors per host (top 5)
    pipeline = [
        {"$group": {"_id": "$host_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    host_stats = list(db.visitors.aggregate(pipeline))
    host_labels = [h["_id"] or "Unassigned" for h in host_stats]
    host_counts = [h["count"] for h in host_stats]

    return jsonify({
        "daily": {"labels": days, "values": counts},
        "status": {"labels": status_labels, "values": status_counts},
        "hosts": {"labels": host_labels, "values": host_counts},
    })
