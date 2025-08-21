# app/models/incoming_sms.py
from sqlalchemy import BigInteger, Column, DateTime, String, Integer, UniqueConstraint, Index
from sqlalchemy.sql import func
from app.db.session import Base

class IncomingSMS(Base):
    __tablename__ = "incoming_sms"
    __table_args__ = (
        UniqueConstraint("msg_uid", name="uq_incomingsms_msguid"),
        Index("ix_incomingsms_ref_time", "op_ref", "received_at"),
    )

    id = Column(BigInteger, primary_key=True)
    sender = Column(String(64), nullable=True)
    body = Column(String(1024), nullable=False)
    op_ref = Column(String(128), nullable=True)      # رقم العملية المستخرج
    amount_syp = Column(Integer, nullable=True)      # المبلغ ل.س المستخرج
    received_at = Column(DateTime, nullable=False, server_default=func.now())
    msg_uid = Column(String(128), nullable=True)     # معرّف الرسالة من الهاتف إن وجد
    consumed_at = Column(DateTime, nullable=True)    # وقت استهلاكها للمطابقة
