# app/webhooks/sms.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.wallet_transaction import WalletTransaction
from app.repositories.wallet_txn_repo import approve_topup, AlreadyFinalizedError
from app.core.config import settings
import re

router = APIRouter(prefix="/webhook", tags=["sms"])

class SmsPayload(BaseModel):
    secret: str
    sender: str
    body: str
    msg_uid: str | None = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# استخراج المرجع من نص الرسالة
REF_PATTERN = r"(?:رقم\s*العملية|مرجع|Ref)[:\s\-]*([A-Za-z0-9\-]+)"

def extract_ref(text: str) -> str | None:
    m = re.search(REF_PATTERN, text)
    if m:
        return m.group(1).strip()
    return None

@router.post("/sms")
def sms_webhook(payload: SmsPayload, db: Session = Depends(get_db)):
    # تحقق السر
    if payload.secret != settings.SMS_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    ref = extract_ref(payload.body) or (payload.body.strip()[:64])
    if not ref:
        return {"matched": False, "reason": "no_ref_found"}

    # ابحث عن معاملة pending بنفس المرجع
    tx = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.type == "topup",
            WalletTransaction.status == "pending",
            WalletTransaction.note == "syriatelcash",
            WalletTransaction.operation_ref_or_txid == ref,
        )
        .first()
    )
    if not tx:
        return {"matched": False, "reason": "no_pending_tx"}

    try:
        tx = approve_topup(db, tx.id)
        return {"matched": True, "approved": True, "tx_id": tx.id}
    except AlreadyFinalizedError:
        return {"matched": True, "approved": False, "reason": "already_final"}
