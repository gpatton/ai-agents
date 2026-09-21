import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from dotenv import load_dotenv

load_dotenv()

CLERK_ISSUER = os.environ["CLERK_ISSUER"].rstrip("/")

CLERK_JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"

jwks_client = PyJWKClient(CLERK_JWKS_URL)

def verify_clerk_token(token: str) -> dict:
    """Validate a Clerk JWT and return its verified claims."""

    signing_key = jwks_client.get_signing_key_from_jwt(token)

    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=CLERK_ISSUER,
        audience="agentforge-api",
        options={
            "require": ["exp", "iat", "iss", "sub", "aud"],
        },
    )

    return claims

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> str:
    """Return the Clerk user ID from a verified bearer token."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verify_clerk_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user_id = claims.get("sub")

    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id

test_app = FastAPI()


@test_app.get("/protected")
def protected_endpoint(
    user_id: str = Depends(get_current_user_id),
):
    return {"user_id": user_id}


def test_missing_bearer_token():
    client = TestClient(test_app)

    response = client.get("/protected")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_invalid_bearer_token():
    client = TestClient(test_app)

    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_valid_bearer_token():
    client = TestClient(test_app)

    response = client.get(
        "/protected",
        headers={
            "Authorization": f"Bearer {make_token()}",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": TEST_USER_ID,
    }
