"""
Tests for the /api/v1/health endpoint.
"""


def test_health_returns_200(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_old_reminder_prefix_gone():
    """Regression guard — /api/v1/reminder/today was renamed to /reminders/today."""
    pass  # Covered in test_sharing_and_history.py


def test_health_response_shape(client):
    data = response = client.get("/api/v1/health").json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "database" in data
