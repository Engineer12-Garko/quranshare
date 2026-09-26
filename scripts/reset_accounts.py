import os
import sys

# Ensure app modules can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from app.database import SessionLocal
from app.models.user import User
from app.models.posting_history import PostingHistory

def reset_accounts():
    db = SessionLocal()
    try:
        # Delete dependent tables first
        db.query(PostingHistory).delete()
        # Delete all users
        deleted_users = db.query(User).delete()
        
        db.commit()
        print(f"✅ Successfully deleted {deleted_users} accounts and their posting history!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting accounts: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_accounts()
