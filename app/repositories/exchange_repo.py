from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.exchange_rate import ExchangeRate

def get_rate(db: Session, from_currency: str, to_currency: str) -> Decimal | None:
    row = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
        )
        .one_or_none()
    )
    return Decimal(row.value) if row else None
