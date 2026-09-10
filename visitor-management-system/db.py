"""
db.py
-----
Handles the MongoDB connection for the Smart Visitor Management System
and creates the indexes the app relies on. Uses PyMongo directly (no ORM)
so the data model stays simple and transparent for a student/academic
project, while still being production-shaped.

Serverless-safe: connection is established lazily on first request,
not at module import time (required for Vercel/serverless environments).
"""
import os
import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash

_client = None
_db = None
_app_config = None


def init_db(app):
    """Called once from app.py during application startup.
    Stores config for lazy connection — does NOT connect immediately.
    This is required for Vercel serverless cold-start compatibility.
    """
    global _app_config
    _app_config = app.config
    app.logger.info("DB config stored. Connection will be made on first request.")


def _connect():
    """Internal: establish MongoDB connection if not already connected."""
    global _client, _db

    if _db is not None:
        return _db

    # Fall back to env vars directly if _app_config not set
    mongo_uri = (
        (_app_config.get("MONGO_URI") if _app_config else None)
        or os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    )
    mongo_db_name = (
        (_app_config.get("MONGO_DB_NAME") if _app_config else None)
        or os.environ.get("MONGO_DB_NAME", "visitor_management")
    )

    _client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,   # fail fast if unreachable
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
    )
    _db = _client[mongo_db_name]

    _create_indexes()
    return _db


def get_db():
    """Return the active database, connecting lazily if needed."""
    return _connect()


def seed_admin_if_needed():
    """Seed default admin on first run. Called from a route, not at startup."""
    db = get_db()

    if db.users.count_documents({"role": "admin"}) > 0:
        return  # already seeded

    username = (
        (_app_config.get("DEFAULT_ADMIN_USERNAME") if _app_config else None)
        or os.environ.get("DEFAULT_ADMIN_USERNAME", "admin")
    )
    password = (
        (_app_config.get("DEFAULT_ADMIN_PASSWORD") if _app_config else None)
        or os.environ.get("DEFAULT_ADMIN_PASSWORD", "Admin@123")
    )
    email = (
        (_app_config.get("DEFAULT_ADMIN_EMAIL") if _app_config else None)
        or os.environ.get("DEFAULT_ADMIN_EMAIL", "admin@vms.local")
    )

    db.users.insert_one({
        "username": username,
        "email": email,
        "password_hash": generate_password_hash(password),
        "full_name": "System Administrator",
        "role": "admin",
        "department": "Administration",
        "is_active": True,
        "created_at": datetime.datetime.utcnow(),
    })


def _create_indexes():
    db = _db
    db.users.create_index([("username", ASCENDING)], unique=True)
    db.users.create_index([("email", ASCENDING)], unique=True)

    db.visitors.create_index([("pass_id", ASCENDING)], unique=True)
    db.visitors.create_index([("status", ASCENDING)])
    db.visitors.create_index([("host_id", ASCENDING)])
    db.visitors.create_index([("created_at", DESCENDING)])

    db.notifications.create_index([("host_id", ASCENDING), ("is_read", ASCENDING)])
    db.notifications.create_index([("created_at", DESCENDING)])

    db.checkin_logs.create_index([("visitor_id", ASCENDING)])
    db.checkin_logs.create_index([("timestamp", DESCENDING)])
