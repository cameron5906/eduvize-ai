from typing import Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.routing.responses import raise_unauthorized
from app.utilities.jwt import InvalidJWTToken, decode_token
from app.services.auth_service import TOKEN_BLACKLIST_SET
from common.cache import is_in_set_with_expiration
from config import get_token_secret

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def token_validator(
    token: str = Depends(oauth2_scheme)
) -> dict:
    """
    Extracts the JWT information from the request token while also ensuring it is not blacklisted

    Args:
        token (str, optional): The token provided in an HTTP request.

    Raises:
        HTTPException: 401 - Invalid token received

    Returns:
        dict: The decoded token information
    """
    try:
        data = decode_token(token, get_token_secret())
    
        if is_in_set_with_expiration(TOKEN_BLACKLIST_SET, token):
            raise_unauthorized()
            
        return data
    except InvalidJWTToken:
        raise_unauthorized()
        
def get_access_token(token: str = Depends(oauth2_scheme)) -> Optional[str]:
    """
    Extracts the access token from the token in the request

    Args:
        token (str): The token provided in an HTTP request

    Returns:
        str: The access token
    """
    
    try:
        return token
    except InvalidJWTToken:
        return None
    
def user_id_extractor(token: dict = Depends(token_validator)) -> str:
    """
    Extracts the authorized user's ID from the token in the request

    Args:
        token (dict, optional): The decoded token information from the request

    Returns:
        str: The user's ID
    """
    return token.get("id")