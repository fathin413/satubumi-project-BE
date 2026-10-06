from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    profile_image = Column(String(500), nullable=True)
    role = Column(String(50), default="client")  # admin, client, analyst
    is_active = Column(Boolean, default=True)
    has_rapidfs_access = Column(Boolean, default=False, nullable=False)
    rapidfs_request_status = Column(String(50), nullable=True)  # pending, approved, rejected
    rapidfs_requested_at = Column(DateTime, nullable=True)
    rapidfs_request_project = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
