from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text, JSON

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location_name = Column(String(255), nullable=False)
    area_ha = Column(Float, nullable=True)

    # Status proyek: active, completed, suspended
    status = Column(String(50), default="active", nullable=False)

    # Tipe proyek: reforestation, mangrove, agroforestry, peatland, blue_carbon, etc.
    project_type = Column(String(100), nullable=True)

    # Durasi proyek
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Lokasi administratif
    country = Column(String(100), nullable=True, default="Indonesia")
    province = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)

    # Batas wilayah proyek dalam format GeoJSON (Polygon)
    boundary_geojson = Column(JSON, nullable=True)

    # Target proyek (disimpan sebagai JSON agar fleksibel)
    # Contoh: {"restoration_ha": 1000, "tree_planting": 100000}
    targets_json = Column(JSON, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

