import secrets
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.exceptions.security import TokenExpiredError, InvalidTokenError

app = FastAPI()


@app.exception_handler(TokenExpiredError)
async def token_expired_handler(request: Request, exc: TokenExpiredError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a secure random token.

    Returns:
        str: Securely generated token.
    """
    return secrets.token_urlsafe(length)
