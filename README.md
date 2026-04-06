# Finance Tracker Backend

A Python-based finance tracking system built with **FastAPI**, **SQLAlchemy**, and **SQLite**. It supports full financial record management, analytics summaries, and role-based access control via JWT authentication.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Framework | FastAPI |
| Database | SQLite (via SQLAlchemy ORM) |
| Auth | JWT (python-jose + passlib) |
| Validation | Pydantic v2 |
| Server | Uvicorn |

---

## Project Structure

```
finance-tracker-backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # All FastAPI routes
│   ├── database.py      # SQLite engine + session
│   ├── models.py        # SQLAlchemy DB models
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # JWT creation, verification, role deps
│   └── summary.py       # Analytics and summary logic
├── .env                 # Your local environment variables (not committed)
├── .env.example         # Template for environment variables
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/UrvishAhir1/finance-tracker-backend.git
cd finance-tracker-backend
```

### 2. Create a virtual environment

```bash
# Create venv
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and set your own `SECRET_KEY`:

```
SECRET_KEY=your-very-secret-key-here
DATABASE_URL=sqlite:///./finance.db
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

The app will be available at: **http://127.0.0.1:8000**

> The SQLite database file (`finance.db`) is created automatically on first run. No setup needed.

---

## API Documentation

FastAPI generates interactive docs automatically:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

---

## User Roles

| Role | Permissions |
|---|---|
| `viewer` | View transactions, view overview & recent summary |
| `analyst` | All viewer permissions + category breakdown + monthly totals |
| `admin` | Full access: create, update, delete transactions + manage users |

> All new users registered via `/auth/register` are assigned the `viewer` role by default. An admin can promote users via `/users/{id}/role`.

---

## API Endpoints

### Auth

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Register a new user |
| POST | `/auth/login` | Public | Login and get JWT token |
| GET | `/auth/me` | Any logged-in user | Get current user info |

### Transactions

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/transactions` | Admin | Create a new transaction |
| GET | `/transactions` | Viewer+ | List transactions with filters + pagination |
| GET | `/transactions/{id}` | Viewer+ | Get a single transaction |
| PUT | `/transactions/{id}` | Admin | Update a transaction |
| DELETE | `/transactions/{id}` | Admin | Delete a transaction |

**Query parameters for GET /transactions:**

| Parameter | Type | Description |
|---|---|---|
| `type` | `income` or `expense` | Filter by transaction type |
| `category` | string | Filter by category (partial match) |
| `date_from` | YYYY-MM-DD | Filter from date |
| `date_to` | YYYY-MM-DD | Filter to date |
| `search` | string | Search in category or notes |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Results per page (default: 10, max: 100) |

### Summary

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/summary/overview` | Viewer+ | Total income, expenses, balance |
| GET | `/summary/by-category` | Analyst+ | Breakdown per category |
| GET | `/summary/monthly` | Analyst+ | Month-wise income vs expense |
| GET | `/summary/recent` | Viewer+ | Last 10 transactions |

### Users

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/users` | Admin | List all users |
| PUT | `/users/{id}/role` | Admin | Update a user's role |

---

## How to Test (Step by Step)

Open **http://127.0.0.1:8000/docs** in your browser.

### Step 1: Register a user
```json
POST /auth/register
{
  "name": "Admin User",
  "email": "admin@example.com",
  "password": "secret123"
}
```

### Step 2: Login and copy the token
```json
POST /auth/login
{
  "email": "admin@example.com",
  "password": "secret123"
}
```
Copy the `access_token` from the response.

### Step 3: Authorize in Swagger
1. Login via `POST /auth/login` and copy the `access_token`
2. Click the **Authorize** 🔒 button (top right in Swagger UI)
3. A popup opens — scroll down to the **HTTPBearer** section
4. Paste your token in the **Value** field (no "Bearer" prefix needed)
5. Click **Authorize** → **Close**

You will see a locked padlock on all endpoints — you are now authorized.

### Step 4: Promote yourself to admin
Since your first registered user is a viewer by default, run this command once from your project folder (with venv active):

```bash
python -c "from app.database import SessionLocal; from app.models import User, UserRole; db = SessionLocal(); u = db.query(User).first(); u.role = UserRole.admin; db.commit(); print('Done! Admin role set for:', u.email)"
```

Then login again to get a fresh token with the admin role. Alternatively, use [DB Browser for SQLite](https://sqlitebrowser.org/) to manually set `role = 'admin'` in the `users` table.

### Step 5: Create transactions
```json
POST /transactions
{
  "amount": 5000.00,
  "type": "income",
  "category": "Salary",
  "date": "2024-01-15",
  "notes": "January salary"
}
```

### Step 6: View summaries
```
GET /summary/overview
GET /summary/by-category
GET /summary/monthly
```

---

## Data Models

### Transaction

| Field | Type | Description |
|---|---|---|
| `id` | integer | Auto-generated primary key |
| `amount` | float | Must be greater than 0 |
| `type` | enum | `income` or `expense` |
| `category` | string | e.g. Salary, Food, Rent |
| `date` | date | YYYY-MM-DD format |
| `notes` | string | Optional description |
| `user_id` | integer | FK to user who created it |

### User

| Field | Type | Description |
|---|---|---|
| `id` | integer | Auto-generated primary key |
| `name` | string | Full name |
| `email` | string | Unique, used for login |
| `role` | enum | `viewer`, `analyst`, or `admin` |

---

## Assumptions Made

- All new users start as `viewer`. Role escalation is done by an admin.
- Transactions are global (not scoped per user). The `user_id` field tracks who created the record.
- The first admin must be manually set in the database (one-time setup), since there's no bootstrap admin endpoint.
- SQLite is used for simplicity. Switching to PostgreSQL only requires changing `DATABASE_URL` in `.env`.
- JWT tokens expire after 60 minutes by default (configurable via `.env`).

---

## Dependencies

```
fastapi          - Web framework
uvicorn          - ASGI server
sqlalchemy       - ORM and database layer
python-jose      - JWT encoding/decoding
passlib[bcrypt]  - Password hashing
python-dotenv    - Load .env variables
pydantic[email]  - Validation and email support
```
---

**Author:** Urvish Ahir