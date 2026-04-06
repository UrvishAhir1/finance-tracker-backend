from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.models import Transaction, TransactionType
from collections import defaultdict


def get_overview(db: Session) -> dict:
    rows = db.query(Transaction.type, func.sum(Transaction.amount)).group_by(Transaction.type).all()

    totals = {r[0]: r[1] for r in rows}
    income = totals.get(TransactionType.income, 0.0)
    expense = totals.get(TransactionType.expense, 0.0)

    return {
        "total_income": round(income, 2),
        "total_expenses": round(expense, 2),
        "balance": round(income - expense, 2),
    }


def get_by_category(db: Session) -> list:
    rows = (
        db.query(Transaction.category, Transaction.type, func.sum(Transaction.amount))
        .group_by(Transaction.category, Transaction.type)
        .all()
    )

    result = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for category, t_type, total in rows:
        result[category][t_type.value] += round(total, 2)

    return [{"category": cat, **amounts} for cat, amounts in result.items()]


def get_monthly_totals(db: Session) -> list:
    rows = (
        db.query(
            extract("year", Transaction.date).label("year"),
            extract("month", Transaction.date).label("month"),
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .group_by("year", "month", Transaction.type)
        .order_by("year", "month")
        .all()
    )

    monthly = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for year, month, t_type, total in rows:
        key = f"{int(year)}-{int(month):02d}"
        monthly[key][t_type.value] += round(total, 2)

    return [{"month": k, **v} for k, v in monthly.items()]


def get_recent(db: Session, limit: int = 10) -> list:
    rows = (
        db.query(Transaction)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return rows