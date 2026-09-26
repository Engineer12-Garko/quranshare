from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PostingHistory(Base):
    __tablename__ = "posting_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("videos.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # "share_initiated" | "posted"
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    posted_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<PostingHistory id={self.id} user={self.user_id} video={self.video_id} action={self.action}>"
