from sqlalchemy.orm import Session
from app.models.topup_method import TopupMethod

def list_active(db: Session) -> list[TopupMethod]:
    return (
        db.query(TopupMethod)
        .filter(TopupMethod.is_active == True)
        .order_by(TopupMethod.id.asc())
        .all()
    )

def get_by_id(db: Session, method_id: int) -> TopupMethod | None:
    return (
        db.query(TopupMethod)
        .filter(TopupMethod.id == method_id)
        .one_or_none()
    )
