# app/webhooks/sms.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.session import SessionLocal
from app.core.config import settings
from app.models.incoming_sms import IncomingSMS  # تأكد أن الموديل موجود
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

# Regex بسيط لاستخراج المرجع والمبلغ
REF_PATTERNS = [
    r"(?:رقم\s*العملية(?:\s*هو)?|مرجع|Ref)\s*[:\-]?\s*([A-Za-z0-9\-]+)",
    r"\b([0-9]{10,})\b",  # fallback: أرقام طويلة
]
AMOUNT_SYP_PATTERNS = [
    r"(\d{3,})\s*(?:ل\.?\s*س|ليرة\s*سورية|SYP)",
    r"تم\s*استلام\s*مبلغ\s*(\d{3,})",
]

def extract_ref(text: str) -> str | None:
    for p in REF_PATTERNS:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None

def extract_amount_syp(text: str) -> int | None:
    for p in AMOUNT_SYP_PATTERNS:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except:
                return None
    return None

@router.post("/sms")
def sms_webhook(payload: SmsPayload, db: Session = Depends(get_db)):
    # 1) تحقق السر
    if payload.secret != settings.SMS_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="unauthorized")

    # 2) استخراج القيم
    body = (payload.body or "")[:1024]
    sender = (payload.sender or "")[:64]
    op_ref = extract_ref(body)
    amount_syp = extract_amount_syp(body)
    msg_uid = (payload.msg_uid or "")[:128] or None

    # 3) خزّن الرسالة
    row = IncomingSMS(
        sender=sender,
        body=body,
        op_ref=(op_ref[:128] if op_ref else None),
        amount_syp=amount_syp,
        msg_uid=msg_uid,
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return {
            "stored": True,
            "dedup": False,
            "id": row.id,
            "ref": row.op_ref,
            "amount_syp": row.amount_syp,
        }
    except IntegrityError:
        # تكرار بحسب msg_uid الفريد
        db.rollback()
        return {
            "stored": False,
            "dedup": True,
            "ref": op_ref,
            "amount_syp": amount_syp,
        }
