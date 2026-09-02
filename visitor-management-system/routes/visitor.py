import datetime
import os
import uuid

import qrcode
from bson.objectid import ObjectId
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, session
)

from db import get_db
from auth_utils import roles_required

visitor_bp = Blueprint("visitor", __name__)


@visitor_bp.route("/visitor/register", methods=["GET", "POST"])
def register():
    """Public kiosk-style visitor registration form (module: Visitor
    Registration & Digital Pass Generation)."""
    db = get_db()
    hosts = list(db.users.find({"role": "host", "is_active": True}).sort("full_name", 1))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        company = request.form.get("company", "").strip()
        purpose = request.form.get("purpose", "").strip()
        host_id = request.form.get("host_id")

        if not (full_name and phone and host_id):
            flash("Name, phone number and host are required.", "error")
            return render_template("visitor_register.html", hosts=hosts)

        host = db.users.find_one({"_id": ObjectId(host_id), "role": "host"})
        if not host:
            flash("Selected host is invalid.", "error")
            return render_template("visitor_register.html", hosts=hosts)

        pass_id = uuid.uuid4().hex[:12].upper()
        now = datetime.datetime.utcnow()

        visitor_doc = {
            "pass_id": pass_id,
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "company": company,
            "purpose": purpose,
            "host_id": str(host["_id"]),
            "host_name": host["full_name"],
            "status": "pending",              # pending -> approved/rejected -> checked_in -> checked_out
            "check_in_time": None,
            "check_out_time": None,
            "created_at": now,
            "valid_until": now + datetime.timedelta(hours=current_app.config["PASS_VALID_HOURS"]),
        }
        result = db.visitors.insert_one(visitor_doc)

        # Generate the QR code for the digital pass (module: QR Code-Based Check-In/Check-Out)
        qr_path = _generate_qr(pass_id)
        db.visitors.update_one({"_id": result.inserted_id}, {"$set": {"qr_path": qr_path}})

        # Notify the host (module: Host Notification & Visitor Approval Workflow)
        db.notifications.insert_one({
            "host_id": str(host["_id"]),
            "visitor_id": str(result.inserted_id),
            "message": f"{full_name} from {company or 'N/A'} is requesting to meet you.",
            "is_read": False,
            "created_at": now,
        })

        flash("Registration submitted! Please wait for host approval.", "success")
        return redirect(url_for("visitor.digital_pass", pass_id=pass_id))

    return render_template("visitor_register.html", hosts=hosts)


def _generate_qr(pass_id):
    """Generate and save a QR code image encoding the visitor's pass_id."""
    folder = current_app.config["QR_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    filename = f"{pass_id}.png"
    filepath = os.path.join(folder, filename)

    img = qrcode.make(pass_id)
    img.save(filepath)

    return f"qrcodes/{filename}"


@visitor_bp.route("/visitor/pass/<pass_id>")
def digital_pass(pass_id):
    """Shows the visitor their digital pass with QR code + live status."""
    db = get_db()
    visitor = db.visitors.find_one({"pass_id": pass_id})
    if not visitor:
        flash("Visitor pass not found.", "error")
        return redirect(url_for("visitor.register"))
    return render_template("visitor_pass.html", visitor=visitor)


@visitor_bp.route("/visitor/pass/<pass_id>/status")
def pass_status(pass_id):
    """Small JSON endpoint the pass page polls so the visitor sees live
    approval / check-in status without reloading."""
    from flask import jsonify
    db = get_db()
    visitor = db.visitors.find_one({"pass_id": pass_id}, {"status": 1})
    if not visitor:
        return jsonify({"error": "not found"}), 404
    return jsonify({"status": visitor["status"]})


@visitor_bp.route("/visitor/login", methods=["GET", "POST"])
def visitor_login():
    """Lets returning visitors look up their pass by Pass ID or phone number."""
    if request.method == "POST":
        lookup_type = request.form.get("lookup_type", "")
        db = get_db()

        if lookup_type == "pass_id":
            pass_id = request.form.get("pass_id", "").strip().upper()
            if not pass_id:
                flash("Please enter your Pass ID.", "error")
                return render_template("visitor_login.html")
            visitor = db.visitors.find_one({"pass_id": pass_id})
            if visitor:
                return redirect(url_for("visitor.digital_pass", pass_id=visitor["pass_id"]))
            flash("No pass found with that ID. Please check and try again.", "error")

        elif lookup_type == "phone":
            phone = request.form.get("phone", "").strip()
            if not phone:
                flash("Please enter your phone number.", "error")
                return render_template("visitor_login.html")
            # Return the most recent pass for this phone number
            visitor = db.visitors.find_one(
                {"phone": phone},
                sort=[("created_at", -1)]
            )
            if visitor:
                return redirect(url_for("visitor.digital_pass", pass_id=visitor["pass_id"]))
            flash("No pass found for that phone number. Please register first.", "error")

        else:
            flash("Please select a search method.", "error")

    return render_template("visitor_login.html")

