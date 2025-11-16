from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import get_settings
from app.v1 import users, teams, projects, tasks, revenues, meetings, dashboards

settings = get_settings()

def get_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(users.router, prefix=settings.API_V1_STR)
    app.include_router(teams.router, prefix=settings.API_V1_STR)
    app.include_router(projects.router, prefix=settings.API_V1_STR)
    app.include_router(tasks.router, prefix=settings.API_V1_STR)
    app.include_router(revenues.router, prefix=settings.API_V1_STR)
    app.include_router(meetings.router, prefix=settings.API_V1_STR)
    app.include_router(dashboards.router, prefix=settings.API_V1_STR)
    return app

app = get_app()
