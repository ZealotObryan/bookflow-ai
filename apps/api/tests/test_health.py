from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "bookflow-api"}


def test_api_root_identifies_version() -> None:
    response = client.get("/api/v1")

    assert response.status_code == 200
    assert response.json() == {"name": "BookFlow AI API", "version": "v1"}
