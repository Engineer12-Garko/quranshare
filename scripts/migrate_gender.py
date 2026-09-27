import sys
import os

# Append current dir to sys.path so we can import app modules
sys.path.append(os.path.abspath("."))

from sqlalchemy import text
from app.database import engine

def add_gender_column():
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(20) DEFAULT 'unspecified';"))
        print("Gender column added successfully!")
    except Exception as e:
        print(f"Error altering table: {e}")

if __name__ == "__main__":
    add_gender_column()
