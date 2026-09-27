import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from app.models.user import User

load_dotenv()
db_url = os.environ["DATABASE_URL"]
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
db = Session()

user = db.query(User).filter(User.email == "garko1001@gmail.com").first()
if user:
    user.role = "admin"
    db.commit()
    print(f"Success! Upgraded {user.email} to admin.")
else:
    print("User not found.")
db.close()
