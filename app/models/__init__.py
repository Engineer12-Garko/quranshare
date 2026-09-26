# Import all models here so Alembic's autogenerate can detect them.
from app.models.user import User
from app.models.category import Category
from app.models.video import Video
from app.models.posting_history import PostingHistory

__all__ = ["User", "Category", "Video", "PostingHistory"]
