from fastapi.testclient import TestClient

from app.api import app, get_agent


class FakeAgent:
    async def ask(self, message: str) -> str:
        return f"Test response: {message}"


def override_get_agent():
    return FakeAgent()


app.dependency_overrides[get_agent] = override_get_agent


def test_health():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "AgentForge",
    }


def test_chat():
    client = TestClient(app)

    response = client.post(
        "/chat",
        json={
            "message": "Hello AgentForge",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "response": "Test response: Hello AgentForge",
    }
