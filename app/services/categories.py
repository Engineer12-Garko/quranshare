"""Categories service."""
from sqlalchemy.orm import Session

from app.models.category import Category


def list_categories(db: Session, active_only: bool = True) -> list[Category]:
    q = db.query(Category)
    if active_only:
        q = q.filter(Category.is_active.is_(True))
    return q.order_by(Category.name).all()
