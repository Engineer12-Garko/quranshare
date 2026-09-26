"""
Seed script — inserts the approved V1 categories.
Run once after the initial migration:

    cd quranflow
    python -m scripts.seed_categories
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models.category import Category

SEED_CATEGORIES = [
    {"name": "Quran",    "description": "Quranic verses and recitations"},
    {"name": "Dua",      "description": "Supplications and prayers"},
    {"name": "Salah",    "description": "Prayer reminders and guidance"},
    {"name": "Patience", "description": "Reminders on sabr and perseverance"},
    {"name": "Tawakkul", "description": "Reminders on trust in Allah"},
    {"name": "Akhirah",  "description": "Reminders about the hereafter"},
    {"name": "General",  "description": "General Islamic reminders"},
]


def seed() -> None:
    db = SessionLocal()
    try:
        inserted = 0
        for cat_data in SEED_CATEGORIES:
            exists = db.query(Category).filter_by(name=cat_data["name"]).first()
            if not exists:
                db.add(Category(**cat_data))
                inserted += 1
        db.commit()
        print(f"Seeded {inserted} categories ({len(SEED_CATEGORIES) - inserted} already existed).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
