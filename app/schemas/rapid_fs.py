from typing import Any

from pydantic import BaseModel, Field


class RapidFSInput(BaseModel):
    location_name: str | None = "Lokasi Proyek Karbon"
    latitude: float | None = None
    longitude: float | None = None
    polygon_geojson: dict[str, Any] | None = None
    area_ha: float = Field(..., gt=0, description="Luas area dalam Hektare")
    ecosystem_type: str = Field(
        "hutan_tropis",
        description="Tipe ekosistem: hutan_tropis, mangrove, agroforestri, gambut, lahan_terdegradasi",
    )
    project_duration_years: int = Field(
        30, ge=1, le=100, description="Durasi proyek dalam tahun"
    )
    carbon_price_usd: float = Field(
        10.0, ge=0, description="Harga kredit karbon per tCO2e dalam USD"
    )


class ComponentScores(BaseModel):
    carbon_score: float = Field(
        ..., ge=0, le=100, description="C: Skor Karbon (Bobot 35%)"
    )
    legality_score: float = Field(
        ..., ge=0, le=100, description="L: Skor Legalitas & Hutan (Bobot 20%)"
    )
    biodiversity_score: float = Field(
        ..., ge=0, le=100, description="B: Skor Keanekaragaman Hayati (Bobot 15%)"
    )
    social_score: float = Field(
        ..., ge=0, le=100, description="S: Skor Akses & Risiko Sosial (Bobot 10%)"
    )
    economy_score: float = Field(
        ..., ge=0, le=100, description="E: Skor Kelayakan Ekonomi (Bobot 20%)"
    )


class CostBreakdown(BaseModel):
    development_cost_usd: float
    mrv_cost_usd: float
    validation_cost_usd: float
    operational_cost_usd: float
    total_cost_usd: float


class RapidFSResult(BaseModel):
    location_name: str
    area_ha: float
    ecosystem_type: str
    project_duration_years: int
    carbon_price_usd: float

    # Karbon metrics
    carbon_factor: float
    emission_reduction_rate: float
    agb_ton: float
    carbon_stock_tc: float
    co2e_ton: float
    annual_emission_reduction: float
    acc_total_credits: float

    # Financial metrics
    gross_revenue_usd: float
    cost_breakdown: CostBreakdown
    net_revenue_usd: float

    # Feasibility score
    feasibility_score: float
    feasibility_category: str
    component_scores: ComponentScores
    recommendations: list[str]

    # Tahap 2: 9 Layer Spasial Overlay & Geometry
    spatial_overlay_layers: dict[str, Any] | None = None
    geometry: dict[str, Any] | None = None
