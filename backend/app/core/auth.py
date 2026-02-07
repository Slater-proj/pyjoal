"""
Authentication middleware for API endpoints
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader, APIKeyQuery
from typing import Optional
import hmac

from app.core.config import settings

# Accept token from header or query parameter
api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)
api_key_query = APIKeyQuery(name="token", auto_error=False)


async def verify_token(
    header_token: Optional[str] = Security(api_key_header),
    query_token: Optional[str] = Security(api_key_query)
) -> str:
    """
    Verify API token from header or query parameter
    Raises 401 if token is invalid or missing
    """
    token = header_token or query_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token. Provide X-API-Token header or ?token=... query parameter"
        )
    
    if not hmac.compare_digest(token, settings.SECRET_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return token
