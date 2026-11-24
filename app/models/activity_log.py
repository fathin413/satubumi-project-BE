from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from datetime import datetime

from app.core.database import Base


class ActivityLog(Base):

    __tablename__ = "activity_logs"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )


    action = Column(
        String(50),
        nullable=False
    )


    module = Column(
        String(100),
        nullable=False
    )


    target_id = Column(
        Integer,
        nullable=True
    )


    target_name = Column(
        String(255),
        nullable=True
    )


    description = Column(
        Text,
        nullable=True
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )