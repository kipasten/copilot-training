from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import app, activities

# Preserve a clean copy of the in-memory database for each test
_initial_state = deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_state():
    activities.clear()
    activities.update(deepcopy(_initial_state))
    yield
    activities.clear()
    activities.update(deepcopy(_initial_state))


def get_client():
    return TestClient(app)


def test_get_activities_lists_entries():
    client = get_client()
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert "Chess Club" in data
    assert isinstance(data["Chess Club"]["participants"], list)


def test_signup_adds_participant_and_prevents_duplicates():
    client = get_client()
    email = "newstudent@mergington.edu"

    first = client.post(f"/activities/Chess%20Club/signup?email={email}")
    assert first.status_code == 200
    assert "Signed up" in first.json()["message"]

    duplicate = client.post(f"/activities/Chess%20Club/signup?email={email}")
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Student already signed up for this activity"


def test_unregister_removes_participant_and_handles_missing():
    client = get_client()
    email = "temp@mergington.edu"

    signup = client.post(f"/activities/Chess%20Club/signup?email={email}")
    assert signup.status_code == 200

    deleted = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
    assert deleted.status_code == 200
    assert "Removed" in deleted.json()["message"]

    after = client.get("/activities")
    assert email not in after.json()["Chess Club"]["participants"]

    missing = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Student not registered for this activity"


def test_unregister_handles_invalid_activity():
    client = get_client()
    response = client.delete(f"/activities/NonExistent/unregister?email=test@example.com")
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_requires_valid_email():
    client = get_client()
    response = client.post("/activities/Chess%20Club/signup?email=")
    assert response.status_code == 400
    assert response.json()["detail"] == "Email is required"


def test_unregister_requires_valid_email():
    client = get_client()
    response = client.delete("/activities/Chess%20Club/unregister?email=")
    assert response.status_code == 400
    assert response.json()["detail"] == "Email is required"


def test_signup_respects_max_participants():
    client = get_client()
    # Chess Club has max_participants of 12, and starts with 2 participants
    # Fill it to capacity
    for i in range(10):
        email = f"student{i}@mergington.edu"
        response = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response.status_code == 200
    
    # Try to add one more participant - should fail
    response = client.post(f"/activities/Chess%20Club/signup?email=overflow@mergington.edu")
    assert response.status_code == 400
    assert response.json()["detail"] == "Activity is at full capacity"
