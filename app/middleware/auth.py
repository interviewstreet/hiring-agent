import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

security = HTTPBearer()

API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "")


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Validate the Bearer token from the Authorization header."""
    if not API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_AUTH_TOKEN is not configured on the server.",
        )

    if credentials.credentials != API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
