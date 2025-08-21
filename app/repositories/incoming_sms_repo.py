# app/repositories/incoming_sms_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from sqlalchemy.dialects.mysql import insert
from datetime import datetime, timedelta
from app.models.incoming_sms import IncomingSMS

def claim_matching_sms(
    db: Session,
    *,
    op_ref: str,
    amount_syp: int | None,
    tolerance: int,
    window_minutes: int = 240,
) -> IncomingSMS | None:
    t0 = datetime.utcnow() - timedelta(minutes=window_minutes)
    q = (
        select(IncomingSMS)
        .where(
            IncomingSMS.op_ref == op_ref,
            IncomingSMS.consumed_at.is_(None),
            IncomingSMS.received_at >= t0,
        )
        .order_by(IncomingSMS.received_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    row = db.execute(q).scalar_one_or_none()
    if not row:
        return None
    if amount_syp is not None and row.amount_syp is not None:
        if abs(int(row.amount_syp) - int(amount_syp)) > int(tolerance):
            return None
    row.consumed_at = datetime.utcnow()
    db.add(row)
    return row
