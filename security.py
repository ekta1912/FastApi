from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from config import get_settings
from exceptions import AuthenticationError

settings = get_settings()
api_key_header = APIKeyHeader(name=settings.api_key_header_name, auto_error=False)

def verify_admin_key(api_key: str = Security(api_key_header)) -> str:
    """Validate administrator API key from request headers."""
    expected_key = settings.admin_api_key
    if not api_key or api_key != expected_key:
        raise AuthenticationError("Invalid or missing administrative API key")
    return api_key
