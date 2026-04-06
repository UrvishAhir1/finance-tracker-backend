from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.database import get_db, engine
from app import models
from app.models import User, Transaction, TransactionType, UserRole
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    TransactionCreate, TransactionUpdate, TransactionResponse,
    PaginatedTransactions, UserResponse, UpdateRoleRequest
)
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_viewer, require_analyst, require_admin
)
import app.summary as summary_service

# Create all tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Finance Tracker API",
    description="A backend finance tracking system with role-based access control.",
    version="1.0.0"
)


# Auth Routes

@app.post("/auth/register", response_model=TokenResponse, status_code=201, tags=["Auth"])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.viewer
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token, "token_type": "bearer", "role": user.role.value}


@app.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token, "token_type": "bearer", "role": user.role.value}


@app.get("/auth/me", response_model=UserResponse, tags=["Auth"])
def me(current_user: User = Depends(get_current_user)):
    return current_user


# Transaction Routes

@app.post("/transactions", response_model=TransactionResponse, status_code=201, tags=["Transactions"])
def create_transaction(
    body: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    tx = Transaction(**body.model_dump(), user_id=current_user.id)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@app.get("/transactions", response_model=PaginatedTransactions, tags=["Transactions"])
def list_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer),
    
    # Filters
    type: Optional[TransactionType] = Query(None, description="Filter by income or expense"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    date_from: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    
    # Search
    search: Optional[str] = Query(None, description="Search in category or notes"),

    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Results per page"),
):
    query = db.query(Transaction)

    if type:
        query = query.filter(Transaction.type == type)
    if category:
        query = query.filter(Transaction.category.ilike(f"%{category}%"))
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if search:
        query = query.filter(
            Transaction.category.ilike(f"%{search}%") |
            Transaction.notes.ilike(f"%{search}%")
        )

    total = query.count()
    results = query.order_by(Transaction.date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {"total": total, "page": page, "page_size": page_size, "results": results}


@app.get("/transactions/{tx_id}", response_model=TransactionResponse, tags=["Transactions"])
def get_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer)
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@app.put("/transactions/{tx_id}", response_model=TransactionResponse, tags=["Transactions"])
def update_transaction(
    tx_id: int,
    body: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tx, field, value)

    db.commit()
    db.refresh(tx)
    return tx


@app.delete("/transactions/{tx_id}", status_code=204, tags=["Transactions"])
def delete_transaction(
    tx_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()


# Summary Routes

@app.get("/summary/overview", tags=["Summary"])
def overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer)
):
    return summary_service.get_overview(db)


@app.get("/summary/by-category", tags=["Summary"])
def by_category(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst)
):
    return summary_service.get_by_category(db)


@app.get("/summary/monthly", tags=["Summary"])
def monthly(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_analyst)
):
    return summary_service.get_monthly_totals(db)


@app.get("/summary/recent", tags=["Summary"])
def recent(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_viewer)
):
    rows = summary_service.get_recent(db)
    return [TransactionResponse.model_validate(r) for r in rows]


# User Management Routes

@app.get("/users", response_model=list[UserResponse], tags=["Users"])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    return db.query(User).all()


@app.put("/users/{user_id}/role", response_model=UserResponse, tags=["Users"])
def update_role(
    user_id: int,
    body: UpdateRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user.role = body.role
    db.commit()
    db.refresh(user)
    return user