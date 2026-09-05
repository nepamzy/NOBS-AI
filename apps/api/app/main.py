from fastapi import FastAPI

from app.routers import health, projects, videos

app = FastAPI(title="NOBS AI API", version="0.1.0")

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(videos.router)
