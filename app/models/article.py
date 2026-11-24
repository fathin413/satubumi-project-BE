from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)

    category = Column(String(50), nullable=False, index=True)
    # about | services | home | insight | general

    title = Column(String(255), nullable=False)

    title_en = Column(String(255), nullable=True)

    slug = Column(String(255), unique=True, index=True)

    # Author lama (tetap dipertahankan untuk artikel existing)
    author = Column(String(255), default="Satubumi Team")

    # Relasi baru ke tabel users
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    author_user = relationship("User", foreign_keys=[author_id])

    content = Column(Text, nullable=False)

    content_en = Column(Text, nullable=True)

    status = Column(String(30), default="published")
    # published | draft

    tags = Column(String(255), nullable=True)

    image_url = Column(String(500), nullable=True)

    # --- Insights ---

    topic = Column(String(50), nullable=True, index=True)
    # carbon | esg | policy | nature | other

    is_featured = Column(Boolean, default=False, index=True)

    view_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
