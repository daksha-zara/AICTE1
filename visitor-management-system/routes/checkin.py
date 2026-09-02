import datetime
from flask import Blueprint, render_template, request, jsonify

from db import get_db
from auth_utils import roles_required

checkin_bp = Blueprint("checkin", __name__)


@checkin_bp.route("/checkin")
@roles_required("security", "admin")
def scan_page():
    """Camera-based QR scanner page (uses the html5-qrcode JS library) with
    a manual pass-ID fallback, for the gate/reception desk."""
    return render_template("checkin.html")


@checkin_bp.route("/checkin/process", methods=["POST"])
@roles_required("security", "admin")
def process():
    """Called by the scanner page (AJAX) with a scanned/typed pass_id.
    Automatically decides whether this is a check-in or a check-out."""
    db = get_db()
    pass_id = (request.json or {}).get("pass_id", "").strip().upper()

    if not pass_id:
        return jsonify({"ok": False, "message": "No pass ID provided."}), 400

    visitor = db.visitors.find_one({"pass_id": pass_id})
    if not visitor:
        return jsonify({"ok": False, "message": "Invalid QR code / pass ID."}), 404

    now = datetime.datetime.utcnow()

    if visitor["status"] == "pending":
        return jsonify({"ok": False, "message": f"{visitor['full_name']} is still awaiting host approval."}), 409

    if visitor["status"] == "rejected":
        return jsonify({"ok": False, "message": f"{visitor['full_name']}'s visit was rejected by the host."}), 409

    if visitor["status"] == "approved":
        db.visitors.update_one({"_id": visitor["_id"]}, {"$set": {"status": "checked_in", "check_in_time": now}})
        db.checkin_logs.insert_one({"visitor_id": str(visitor["_id"]), "action": "check_in", "timestamp": now})
        return jsonify({
            "ok": True,
            "action": "check_in",
            "message": f"{visitor['full_name']} checked IN to meet {visitor['host_name']}.",
            "visitor": {"name": visitor["full_name"], "host": visitor["host_name"], "company": visitor.get("company", "")},
        })

    if visitor["status"] == "checked_in":
        db.visitors.update_one({"_id": visitor["_id"]}, {"$set": {"status": "checked_out", "check_out_time": now}})
        db.checkin_logs.insert_one({"visitor_id": str(visitor["_id"]), "action": "check_out", "timestamp": now})
        return jsonify({
            "ok": True,
            "action": "check_out",
            "message": f"{visitor['full_name']} checked OUT. Have a nice day!",
            "visitor": {"name": visitor["full_name"], "host": visitor["host_name"], "company": visitor.get("company", "")},
        })

    if visitor["status"] == "checked_out":
        return jsonify({"ok": False, "message": f"{visitor['full_name']} has already completed their visit today."}), 409

    return jsonify({"ok": False, "message": "Unknown visitor status."}), 400
