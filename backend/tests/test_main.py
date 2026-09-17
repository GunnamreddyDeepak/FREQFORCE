from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_app_starts():
    """Verifies that the FastAPI application initializes without error."""
    assert app.title == "KISANQUEUE API"
    assert app.version == "2.0.0"


def test_health_endpoint():
    """Verifies that the basic /health liveness check returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "kisanqueue-backend"
