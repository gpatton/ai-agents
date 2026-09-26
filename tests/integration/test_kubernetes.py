import os

import pytest
import requests


BACKEND_URL = os.getenv(
    "AGENTFORGE_TEST_API_URL",
    "http://127.0.0.1:8002",
)

FRONTEND_URL = os.getenv(
    "AGENTFORGE_TEST_FRONTEND_URL",
    "http://127.0.0.1:8081",
)

pytestmark = pytest.mark.integration


def test_backend_health():
    response = requests.get(
        f"{BACKEND_URL}/health",
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_backend_ready():
    response = requests.get(
        f"{BACKEND_URL}/ready",
        timeout=10,
    )

    assert response.status_code == 200


def test_frontend_available():
    response = requests.get(
        FRONTEND_URL,
        timeout=10,
    )

    assert response.status_code == 200
    assert "html" in response.headers["content-type"].lower()

def test_authentication_required():
    response = requests.get(
        f"{BACKEND_URL}/conversations",
        timeout=10,
    )

    assert response.status_code == 401


def test_invalid_token_rejected():
    response = requests.get(
        f"{BACKEND_URL}/conversations",
        headers={
            "Authorization": "Bearer invalid-test-token"
        },
        timeout=10,
    )

    assert response.status_code == 401

def test_authenticated_access():
    token = os.getenv("AGENTFORGE_TEST_TOKEN")

    if not token:
        pytest.skip("No Clerk test token provided")

    response = requests.get(
        f"{BACKEND_URL}/conversations",
        headers={
            "Authorization": f"Bearer {token}",
        },
        timeout=10,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
