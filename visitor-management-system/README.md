# AI-Powered Smart Visitor Management System

A full-stack, responsive Visitor Management System built with **Python (Flask)**,
**MongoDB**, and **HTML/CSS/JavaScript**. Visitors self-register at a kiosk,
get a digital pass with a QR code, hosts approve/reject requests in real
time, and security staff check visitors in/out by scanning the QR code —
all backed by a live analytics dashboard for admins.

---

## 1. Requirement Analysis & Project Planning

**Actors / Roles**
| Role | Capabilities |
|---|---|
| **Visitor** | Self-register (no login), receive digital pass + QR code |
| **Host** (employee) | Approve/reject visit requests, view own visitors, get notifications |
| **Security** | Scan QR / enter Pass ID to check visitors in and out |
| **Admin** | Manage staff accounts, view all visitors, view analytics dashboard |

**Core workflow**
```
Visitor fills form  →  Pass created (status: pending) + QR generated
                     →  Host notified
Host approves        →  status: approved
Visitor arrives at gate → Security scans QR → status: checked_in
Visitor leaves        → Security scans QR again → status: checked_out
Admin                 → sees everything on live analytics dashboard
```

---

## 2 & 3. UI/UX Design + Frontend Development (Responsive)

- Hand-written, mobile-first CSS (`static/css/style.css`) — no framework
  dependency, single design system (navy / teal palette), CSS Grid +
  Flexbox layouts.
- Responsive breakpoints at `900px`, `720px` (hamburger nav) and `560px`
  (single-column stacking for phones).
- Reusable components: cards, stat cards, badges, tables, forms — all
  defined once in `style.css` and reused across every page.
- `static/js/main.js` handles the mobile nav toggle and flash-message
  auto-dismiss.

## 4. Backend Development (Python / Flask)

- Flask application factory pattern (`app.py` → `create_app()`).
- Organised into **Blueprints**, one per module:
  - `routes/auth.py` — login/logout, staff account management
  - `routes/visitor.py` — visitor self-registration, digital pass
  - `routes/host.py` — host dashboard, approvals, notifications
  - `routes/checkin.py` — QR-based check-in/check-out
  - `routes/admin.py` — admin dashboard & analytics API

## 5. Database Design & Integration (MongoDB)

No ORM is used — raw **PyMongo** for full transparency (`db.py`).

**Collections**

```
users
  { _id, username, email, password_hash, full_name, role: admin|host|security,
    department, is_active, created_at }

visitors
  { _id, pass_id, full_name, phone, email, company, purpose,
    host_id, host_name, status: pending|approved|rejected|checked_in|checked_out,
    check_in_time, check_out_time, created_at, valid_until, qr_path }

notifications
  { _id, host_id, visitor_id, message, is_read, created_at }

checkin_logs
  { _id, visitor_id, action: check_in|check_out, timestamp }
```

Indexes are created automatically on startup (`db._create_indexes()`):
unique index on `users.username`/`email`, unique index on
`visitors.pass_id`, plus indexes on `status`, `host_id`, `created_at` for
fast dashboard queries.

## 6. User Authentication & Role-Based Access Control

- Passwords hashed with Werkzeug's `generate_password_hash` /
  `check_password_hash` (never stored in plain text).
- Server-side sessions (Flask `session`) store `user_id`, `role`,
  `full_name`.
- `auth_utils.py` provides two decorators used across every protected
  route:
  - `@login_required` — must be logged in
  - `@roles_required('admin', 'host')` — must be logged in **and** hold
    one of the listed roles (returns `403` otherwise)
- A default `admin` account is auto-seeded on first run (see below).

## 7. Visitor Registration & Digital Pass Generation

- Public form at `/visitor/register` (no login needed) — name, phone,
  email, company, host, purpose.
- On submit: a unique 12-character `pass_id` is generated (`uuid4`), the
  visitor record is inserted with `status: pending`, and a **QR code
  image** encoding the `pass_id` is generated with the `qrcode` library
  and saved to `static/qrcodes/`.
- The visitor is redirected to `/visitor/pass/<pass_id>` — a printable
  digital pass showing their QR code and live status, which **polls the
  server every 4 seconds** (`/visitor/pass/<pass_id>/status`) so the page
  updates automatically the moment the host approves them, with no manual
  refresh.

## 8. QR Code-Based Check-In & Check-Out System

- `/checkin` (security/admin only) uses the **html5-qrcode** JS library
  to scan a visitor's QR code live via the device camera, with a manual
  Pass-ID entry field as a fallback for damaged prints or camera issues.
- A single endpoint, `POST /checkin/process`, is smart about state:
  - `approved` → marks `checked_in`, stamps `check_in_time`
  - `checked_in` → marks `checked_out`, stamps `check_out_time`
  - `pending` / `rejected` / already `checked_out` → returns a clear
    error message instead of silently failing
- Every scan is written to `checkin_logs` for a full audit trail.

## 9. Host Notification & Visitor Approval Workflow

- The moment a visitor registers, a document is written to
  `notifications` for their chosen host, and the host's dashboard shows
  it immediately along with a **Pending Approvals** table with
  one-click **Approve** / **Reject** buttons.
- (This project notifies in-app for a self-contained demo; see "Going
  Further" below for wiring up real email/SMS.)

## 10. Admin Dashboard & Visitor Analytics

- `/admin/dashboard` shows live stat cards (total visitors, today's
  visitors, currently checked in, pending approvals) plus three
  **Chart.js** charts fed by a JSON API (`/admin/analytics/data`):
  - Line chart — visitor volume, last 7 days
  - Doughnut chart — status breakdown
  - Bar chart — top 5 hosts by visitor count
- `/admin/visitors` — full searchable/filterable visitor log.
- `/admin/users` — create and enable/disable host, security and admin
  accounts.

## 11. Testing, Debugging & Performance Optimization

- All Python modules are checked with `py_compile`; every Jinja2
  template is checked with `jinja2.Environment.parse()` — both are clean
  with zero syntax errors (see `test_syntax.sh` below to re-run).
- MongoDB indexes (see §5) keep dashboard and lookup queries fast even
  as visitor volume grows.
- QR polling on the visitor pass page and unread-notification checks are
  lightweight JSON endpoints, not full page reloads.
- **Manual test checklist** (recommended before submission/demo):
  1. Register a visitor → confirm QR pass renders and host sees a
     notification.
  2. Log in as host → approve the visitor → confirm the visitor's pass
     page updates to "approved" within ~4 seconds.
  3. Log in as security → scan/enter the Pass ID → confirm `checked_in`,
     scan again → confirm `checked_out`.
  4. Log in as admin → confirm dashboard stats and charts reflect the
     above activity.
  5. Try accessing `/admin/dashboard` while logged in as a host → confirm
     a `403 Forbidden` page.

## 12. Project Documentation & Submission

This README **is** the project documentation. It covers architecture,
setup, data model, and every module above — ready to paste into a report
or present directly.

---

## Setup Instructions

### Prerequisites
- Python 3.9+
- MongoDB running locally (`mongod`) or a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster

### 1. Install dependencies
```bash
cd visitor-management-system
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# then edit .env — at minimum set MONGO_URI if not using local default,
# and change SECRET_KEY / DEFAULT_ADMIN_PASSWORD before any real deployment
```

### 3. Run the app
```bash
python app.py
```
Visit **http://localhost:5000** — you'll land on the visitor registration
kiosk page. Staff log in at **http://localhost:5000/login**.

A default admin account is created automatically on first run:
```
username: admin
password: Admin@123
```
**Change this password immediately via the database or by adding a
change-password route before real use.**

### 4. (Optional) Seed sample host/security accounts
```bash
python seed.py
```
Creates two sample hosts and one security account so you can test the
full workflow end to end without manually creating accounts first.

---

## Project Structure
```
visitor-management-system/
├── app.py                  # Flask app factory & routing glue
├── config.py                # Central configuration
├── db.py                    # MongoDB connection + index setup + admin seeding
├── auth_utils.py             # login_required / roles_required decorators
├── seed.py                   # Optional sample-data seeding script
├── requirements.txt
├── .env.example
├── routes/
│   ├── auth.py               # Login, logout, staff account management
│   ├── visitor.py            # Registration, digital pass, QR generation
│   ├── host.py                # Host dashboard, approvals, notifications
│   ├── checkin.py             # QR-based check-in / check-out
│   └── admin.py                # Admin dashboard & analytics JSON API
├── templates/                 # Jinja2 templates (all extend base.html)
└── static/
    ├── css/style.css           # Responsive stylesheet
    ├── js/main.js                # Nav toggle, flash auto-dismiss
    └── qrcodes/                  # Generated QR code images (gitignored)
```

## Going Further (nice extensions if you want to extend this for a
viva/demo)
- Real email/SMS notifications to hosts (e.g. via SendGrid/Twilio) in
  place of the in-app notification.
- Face-photo capture at registration for extra verification.
- "AI" angle: plug in an OCR step to auto-fill visitor details from a
  scanned ID card, or a simple no-show/overstay predictor using
  historical `checkin_logs`.
- Password-change / forgot-password flow for staff accounts.
