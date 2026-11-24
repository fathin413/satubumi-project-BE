from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String

from app.core.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Data kontak submitter (untuk user guest maupun logged-in)
    submitter_name = Column(String(255), nullable=True)
    submitter_phone = Column(String(50), nullable=True)
    submitter_email = Column(String(255), nullable=True)

    location_name = Column(String(255), nullable=False)
    area_ha = Column(Float, nullable=False)
    ecosystem_type = Column(String(100), nullable=False)
    project_duration_years = Column(Integer, default=30)
    carbon_price_usd = Column(Float, default=10.0)

    # Karbon & Financial Results
    agb_ton = Column(Float)
    carbon_stock_tc = Column(Float)
    co2e_ton = Column(Float)
    acc_total_credits = Column(Float)
    gross_revenue_usd = Column(Float)
    total_cost_usd = Column(Float)
    net_revenue_usd = Column(Float)

    # Rapid-FS Scores
    feasibility_score = Column(Float, nullable=False)
    feasibility_category = Column(String(100), nullable=False)

    # JSON Details & Polygon Geometry
    component_scores_json = Column(JSON, nullable=True)
    cost_breakdown_json = Column(JSON, nullable=True)
    geometry_geojson = Column(JSON, nullable=True)
    recommendations_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
