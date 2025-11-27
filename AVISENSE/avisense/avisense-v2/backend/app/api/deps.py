from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

# Supabase client (service role for backend operations)
_supabase_client = None


def get_supabase_client() -> Client:
    """Get Supabase client with service role key."""
    global _supabase_client
    
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
        logger.info("✅ Supabase client initialized")
    
    return _supabase_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Validate JWT token and return current user.
    
    The frontend sends the Supabase auth token in the Authorization header.
    We validate it and extract the user information.
    """
    try:
        token = credentials.credentials
        
        # Verify the JWT token with Supabase
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        return user_response.user
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


async def verify_engine_ownership(
    engine_id: str,
    user,
    supabase: Client = Depends(get_supabase_client)
) -> dict:
    """
    Verify that the current user owns the specified engine.
    
    Args:
        engine_id: Engine UUID
        user: Current authenticated user
        supabase: Supabase client
        
    Returns:
        Engine record if owned by user
        
    Raises:
        HTTPException if engine not found or not owned by user
    """
    try:
        response = supabase.table('engines')\
            .select('*')\
            .eq('id', engine_id)\
            .eq('owner_id', user.id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Engine not found or access denied"
            )
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying engine ownership: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify engine ownership"
        )
