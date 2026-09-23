import os

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.testclient import TestClient
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError

load_dotenv()

CLERK_ISSUER = os.environ["CLERK_ISSUER"].rstrip("/")
CLERK_JWKS_URL = f"{CLERK_ISSUER}/.well-known/jwks.json"

jwks_client = PyJWKClient(CLERK_JWKS_URL)

ALLOWED_AUTHORIZED_PARTIES = {
    "http://127.0.0.1:8001",
    "http://localhost:8001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}


def verify_clerk_token(token: str) -> dict:
    """Validate a Clerk session token and return its verified claims."""
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=CLERK_ISSUER,
        options={
            "require": ["exp", "iat", "iss", "sub"],
            "verify_aud": False,
        },
    )

    if claims.get("azp") not in ALLOWED_AUTHORIZED_PARTIES:
        raise InvalidTokenError("Unexpected authorized party")

    return claims


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
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
    except Exception as exc:
        print(
            f"Clerk verification failed: {type(exc).__name__}",
            flush=True,
        )
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
        headers={"Authorization": f"Bearer {make_token()}"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": TEST_USER_ID}
