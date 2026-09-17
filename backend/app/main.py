import logging
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.session import check_database_connection, check_postgis_available

logger = logging.getLogger("kisanqueue.main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent Procurement Centre Orchestration Platform",
)


@app.get("/health", summary="Basic service liveness check")
def health_check():
    """Returns basic service health status without touching the database."""
    return {
        "status": "ok",
        "service": "kisanqueue-backend",
    }


@app.get("/health/ready", summary="Database and PostGIS readiness check")
def readiness_check():
    """Verifies that the backend can communicate with PostgreSQL and PostGIS.

    Returns 200 OK when the database and spatial extension are operational.
    Returns 503 Service Unavailable if the database is disconnected or unreachable.
    Never exposes credentials or internal passwords in the response.
    """
    db_ok, db_msg = check_database_connection()
    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": "kisanqueue-backend",
                "database": "disconnected",
                "error": db_msg,
            },
        )

    postgis_ok, postgis_version = check_postgis_available()
    if not postgis_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": "kisanqueue-backend",
                "database": "connected",
                "postgis": "unavailable",
                "error": postgis_version,
            },
        )

    return {
        "status": "ready",
        "service": "kisanqueue-backend",
        "database": "connected",
        "postgis": "available",
        "postgis_version": postgis_version,
    }
