import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine
from app.models.article import Article
from app.models.project import Project
from app.models.monitor import (
    ProjectActivity, TreeRecord, TreeMeasurement, FieldReport,
    Alert, BiodiversityObservation, CommunityData, CarbonRecord,
    MonitoringPlot, LandscapeSnapshot, ProjectMember,
)

from app.api.v1.auth import router as auth_router
from app.api.v1.compro.articles import router as articles_router
from app.api.v1.users import router as users_router
from app.api.v1.compro.rapid_fs import router as rapid_fs_router
from app.api.v1.compro.assessments import router as assessments_router
from app.api.v1.compro.reports import router as reports_router
from app.api.v1.compro.contact import router as contact_router
from app.api.v1.compro.currency import router as currency_router
from app.api.v1.compro import insight_topics, rulebooks, team_member
from app.api.v1.monitoring import activity
from app.api.v1.monitoring.projects import router as projects_router
from app.api.v1.monitoring.monitor import router as monitor_router

# Buat folder upload jika belum ada
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Inisialisasi tabel DB saat startup (jika belum ada)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="RESTful API Backend Service untuk Satubumi.org & Rapid-FS Carbon Feasibility Scoring Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Serve static files (gambar upload artikel)
# Akses via: GET /static/uploads/{filename}
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers API v1
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(articles_router, prefix=api_v1_prefix)
app.include_router(users_router, prefix=api_v1_prefix)
app.include_router(rapid_fs_router, prefix=api_v1_prefix)
app.include_router(assessments_router, prefix=api_v1_prefix)
app.include_router(reports_router, prefix=api_v1_prefix)
app.include_router(contact_router, prefix=api_v1_prefix)
app.include_router(currency_router, prefix=api_v1_prefix)
app.include_router(insight_topics.router, prefix=api_v1_prefix)
app.include_router(rulebooks.router, prefix=api_v1_prefix)
app.include_router(team_member.router, prefix=api_v1_prefix)
app.include_router(activity.router, prefix=api_v1_prefix)
app.include_router(projects_router, prefix=api_v1_prefix)
app.include_router(monitor_router, prefix=api_v1_prefix)


@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "docs": "/docs",
        "version": "1.0.0",
    }
