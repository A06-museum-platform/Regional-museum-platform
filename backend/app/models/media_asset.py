"""MediaAsset model — mirrors database/migrations/002_media_assets.sql."""

from datetime import datetime
from typing import Optional

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MediaAsset(Base):
    __tablename__ = "media_asset"

    media_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    collection_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("collection_item.item_id", ondelete="CASCADE")
    )
    exhibition_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("exhibition.exhibition_id", ondelete="CASCADE")
    )
    event_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("event.event_id", ondelete="CASCADE")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(nullable=False)  # 'image' | 'video'
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("user_account.user_id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.current_timestamp()
    )
