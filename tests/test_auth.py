
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.exceptions import InvalidTokenError

from app import auth
from app.auth import get_current_user_id


TEST_USER_ID = "user_test_123"

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

public_key = private_key.public_key()


class FakeSigningKey:
    key = public_key


def make_token(**overrides):
    """Create a signed JWT for authentication tests."""

    now = datetime.now(timezone.utc)

    claims = {
        "sub": TEST_USER_ID,
        "iss": auth.CLERK_ISSUER,
        "aud": "agentforge-api",
        "azp": "http://127.0.0.1:8001",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }

    claims.update(overrides)

    return jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
    )


@pytest.fixture(autouse=True)
def mock_clerk_signing_key(monkeypatch):
    """Use a local test key instead of contacting Clerk."""

    monkeypatch.setattr(
        auth.jwks_client,
        "get_signing_key_from_jwt",
        lambda token: FakeSigningKey(),
    )


def test_valid_token():
    claims = auth.verify_clerk_token(make_token())

    assert claims["sub"] == TEST_USER_ID
    assert claims["aud"] == "agentforge-api"
    assert claims["azp"] == "http://127.0.0.1:8001"


def test_wrong_authorized_party():
    token = make_token(
        azp="https://unauthorized.example.com"
    )

    with pytest.raises(InvalidTokenError):
        auth.verify_clerk_token(token)


def test_expired_token():
    token = make_token(
        exp=datetime.now(timezone.utc)
        - timedelta(minutes=1),
    )

    with pytest.raises(InvalidTokenError):
        auth.verify_clerk_token(token)


def test_different_audience_is_accepted():
    token = make_token(aud="another-application")

    claims = auth.verify_clerk_token(token)

    assert claims["aud"] == "another-application"
    assert claims["sub"] == TEST_USER_ID
    assert claims["azp"] == "http://127.0.0.1:8001"

def test_wrong_issuer():
    token = make_token(
        iss="https://another-issuer.example.com"
    )

    with pytest.raises(InvalidTokenError):
        auth.verify_clerk_token(token)


def test_invalid_signature():
    other_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    token = jwt.encode(
        {
            "sub": TEST_USER_ID,
            "iss": auth.CLERK_ISSUER,
            "aud": "agentforge-api",
            "azp": "http://127.0.0.1:8001",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=5),
        },
        other_private_key,
        algorithm="RS256",
    )

    with pytest.raises(InvalidTokenError):
        auth.verify_clerk_token(token)
