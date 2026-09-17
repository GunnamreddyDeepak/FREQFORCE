import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String

from app.core.config import Settings
from app.db.base_class import Base
from app.db.session import check_database_connection, check_postgis_available
from app.main import app

client = TestClient(app)


class DummyProcurementCenter(Base):
    """Test model for verifying declarative Base class table naming."""
    id = Column(Integer, primary_key=True)
    name = Column(String(50))


def test_declarative_base_naming():
    """Verifies that the Declarative Base automatically derives snake_case table names."""
    assert DummyProcurementCenter.__tablename__ == "dummy_procurement_center"
    assert "dummy_procurement_center" in Base.metadata.tables


def test_database_url_normalization():
    """Verifies that postgresql:// URLs are normalized to postgresql+psycopg://."""
    s = Settings(DATABASE_URL="postgresql://placeholder_user:placeholder_pass@localhost:5432/kisanqueue")
    normalized = s.sqlalchemy_database_url
    assert normalized.startswith("postgresql+psycopg://")
    assert "/kisanqueue" in normalized


def test_database_url_missing_error():
    """Verifies that accessing sqlalchemy_database_url without DATABASE_URL raises ValueError."""
    s = Settings(DATABASE_URL=None)
    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        _ = s.sqlalchemy_database_url


def test_database_connectivity_and_postgis():
    """Verifies PostgreSQL connectivity and PostGIS 3.5 availability against configured database.

    If DATABASE_URL is not configured in the test environment, skips gracefully.
    """
    from app.core.config import settings
    if not settings.DATABASE_URL or "your_password_here" in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured with actual credentials. Skipping live database test.")

    # 1. Verify PostgreSQL SELECT 1
    db_ok, db_msg = check_database_connection()
    assert db_ok is True, f"Database connection failed: {db_msg}"

    # 2. Verify PostGIS extension is available
    postgis_ok, postgis_version = check_postgis_available()
    assert postgis_ok is True, f"PostGIS check failed: {postgis_version}"
    assert "3." in postgis_version or "POSTGIS" in postgis_version.upper()


def test_readiness_endpoint_success():
    """Verifies /health/ready returns 200 OK when database and PostGIS are operational."""
    from app.core.config import settings
    if not settings.DATABASE_URL or "your_password_here" in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured with actual credentials. Skipping live readiness test.")

    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    assert data["postgis"] == "available"
    assert "postgis_version" in data


def test_readiness_endpoint_db_failure():
    """Verifies /health/ready returns 503 when the database check fails, without leaking credentials."""
    with patch("app.main.check_database_connection", return_value=(False, "Database connectivity check failed: ConnectionRefusedError")):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"] == "disconnected"
        assert "password" not in str(data).lower()


def test_readiness_endpoint_postgis_failure():
    """Verifies /health/ready returns 503 when PostGIS is unavailable."""
    with patch("app.main.check_database_connection", return_value=(True, "PostgreSQL connection verified")):
        with patch("app.main.check_postgis_available", return_value=(False, "PostGIS extension not found")):
            response = client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["database"] == "connected"
            assert data["postgis"] == "unavailable"
