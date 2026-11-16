from app.main import app


def test_calendar_feed_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/businesses/{business_id}/calendar/feed" in paths
    assert "/api/v1/calendar/feed/{token}" in paths
    assert "get" in paths["/api/v1/calendar/feed/{token}"]
