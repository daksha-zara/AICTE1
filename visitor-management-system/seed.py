"""
seed.py
-------
Optional helper script to populate the database with a few sample
host/security accounts so you can test the full workflow immediately
after setup.

Usage:
    python seed.py
"""
import datetime
from werkzeug.security import generate_password_hash

from app import app
from db import get_db

SAMPLE_USERS = [
    {"username": "priya.host", "email": "priya@vms.local", "full_name": "Priya Raman", "role": "host", "department": "HR", "password": "Host@123"},
    {"username": "arun.host", "email": "arun@vms.local", "full_name": "Arun Kumar", "role": "host", "department": "Engineering", "password": "Host@123"},
    {"username": "security1", "email": "security1@vms.local", "full_name": "Gate Security", "role": "security", "department": "Facilities", "password": "Security@123"},
]

with app.app_context():
    db = get_db()
    for u in SAMPLE_USERS:
        if db.users.find_one({"username": u["username"]}):
            print(f"Skipping (exists): {u['username']}")
            continue
        db.users.insert_one({
            "username": u["username"],
            "email": u["email"],
            "full_name": u["full_name"],
            "role": u["role"],
            "department": u["department"],
            "password_hash": generate_password_hash(u["password"]),
            "is_active": True,
            "created_at": datetime.datetime.utcnow(),
        })
        print(f"Created {u['role']}: {u['username']} / {u['password']}")

print("\nSeeding complete.")
