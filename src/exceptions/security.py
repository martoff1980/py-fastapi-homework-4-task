from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


class BaseSecurityError(Exception):
    """Base class for all security-related errors."""

    def __init__(self, message=None):
        if message is None:
            message = "A security error occurred."
        super().__init__(message)


class TokenExpiredError(BaseSecurityError):
    """Raised when a token has expired."""

    def __init__(self, message="Token has expired."):
        super().__init__(message)


class InvalidTokenError(BaseSecurityError):
    """Raised when a token is invalid."""

    def __init__(self, message="Invalid token."):
        super().__init__(message)


@app.exception_handler(TokenExpiredError)
async def token_expired_handler(request: Request, exc: TokenExpiredError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})
