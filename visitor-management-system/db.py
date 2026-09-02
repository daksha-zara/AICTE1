"""
db.py
-----
Handles the MongoDB connection for the Smart Visitor Management System
and creates the indexes the app relies on. Uses PyMongo directly (no ORM)
so the data model stays simple and transparent for a student/academic
project, while still being production-shaped.
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash


_client = None
_db = None


def init_db(app):
    """Called once from app.py during application startup."""
    global _client, _db

    _client = MongoClient(app.config["MONGO_URI"])
    _db = _client[app.config["MONGO_DB_NAME"]]

    _create_indexes()
    _seed_default_admin(app)

    app.logger.info("Connected to MongoDB database '%s'", app.config["MONGO_DB_NAME"])
    return _db


def get_db():
    if _db is None:
        raise RuntimeError("Database not initialised. Call init_db(app) first.")
    return _db


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


def _seed_default_admin(app):
    """Create a default admin account the very first time the app runs,
    so there is always at least one way to log in."""
    db = _db
    if db.users.count_documents({"role": "admin"}) > 0:
        return

    db.users.insert_one({
        "username": app.config["DEFAULT_ADMIN_USERNAME"],
        "email": app.config["DEFAULT_ADMIN_EMAIL"],
        "password_hash": generate_password_hash(app.config["DEFAULT_ADMIN_PASSWORD"]),
        "full_name": "System Administrator",
        "role": "admin",
        "department": "Administration",
        "is_active": True,
        "created_at": __import__("datetime").datetime.utcnow(),
    })
    app.logger.info(
        "Seeded default admin account -> username: %s / password: %s (change this immediately)",
        app.config["DEFAULT_ADMIN_USERNAME"], app.config["DEFAULT_ADMIN_PASSWORD"],
    )
