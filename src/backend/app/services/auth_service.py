from time import time
from typing import Optional, Tuple
from fastapi import Depends
from passlib.context import CryptContext
from domain.schema.user import User
from config import get_refresh_token_expiration_days, get_token_expiration_minutes, get_token_secret
from common.cache import add_to_set_with_expiration, is_in_set_with_expiration
from app.utilities.oauth import exchange_github_code_for_token, get_github_user_info, exchange_google_code_for_token, get_google_user_info
from app.utilities.jwt import decode_token
from domain.enums.auth import OAuthProvider
from ..services.user_service import UserService
from ..utilities.jwt import create_token

TOKEN_BLACKLIST_SET = "stale_tokens"
DAYS_TO_MINUTES = 1440
MINUTES_TO_SECONDS = 60

class AuthService:
    """
    Handles all authentication and authorization logic for the application

    Attributes:
        user_service (UserService): The service for interacting with user data
        crypto_context (CryptContext): The context for password hashing and verification
    """
    user_service: UserService
    crypto_context: CryptContext
    
    def __init__(self, user_service: UserService = Depends(UserService)):
        self.user_service = user_service
        
        # Set up a bcrypt provider for password hashing
        self.crypto_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async def authenticate(
        self, 
        email: str, 
        password: str
    ) -> Tuple[str, str, int]:
        """
        Handles authenticating a user and generating an access token

        Args:
            email (str): The user's email address
            password (str): The user's password

        Raises:
            ValueError: Invalid password

        Returns:
            Tuple[str, str, int]: The generated access token, refresh token, and expiration time
        """
        user = await self.user_service.get_user("email", email)
        
        if not self._verify_password(password, user.password_hash):
            raise ValueError("Invalid password")
        
        return self._generate_tokens(str(user.id))
    
    async def register(
        self, 
        email: str, 
        username: str, 
        password: str
    ) -> Tuple[str, str, int]:
        """
        Handles the registration of a new user and generating an access token after successful registration

        Args:
            email (str): The email address of the user
            username (str): The unique name of the user
            password (str): The password of the user

        Returns:
            Tuple[str, str, int]: The generated access token, refresh token and expiration time
        """
        hashed_password = self._get_password_hash(password)
        
        user = await self.user_service.create_user(email, username, hashed_password)
        
        return self._generate_tokens(str(user.id))
    
    def logout(self, access_token: str, refresh_token: str):
        """
        Logs out a user by invalidating their access and refresh tokens

        Args:
            access_token (str): The user's access token
            refresh_token (str): The user's refresh token
        """
        
        decoded_token = decode_token(access_token, get_token_secret())
        decoded_refresh = decode_token(refresh_token, get_token_secret())
        
        exp_token = int(decoded_token["exp"])
        exp_refresh = int(decoded_refresh["exp"])
        
        remaining_token_seconds = exp_token - int(time())
        remaining_refresh_seconds = exp_refresh - int(time())
        
        add_to_set_with_expiration(
            key=TOKEN_BLACKLIST_SET, 
            value=access_token, 
            expiration=remaining_token_seconds
        )
        
        add_to_set_with_expiration(
            key=TOKEN_BLACKLIST_SET, 
            value=refresh_token, 
            expiration=remaining_refresh_seconds
        )
    
    async def refresh_access(
        self,
        refresh_token: str
    ) -> Tuple[str, str, int]:
        """
        Refreshes a user's access token using a valid refresh token

        Args:
            refresh_token (str): The refresh token to use for generating a new access token

        Returns:
            Tuple[str, str, int]: The generated access token, refresh token and expiration time
        """
        
        if is_in_set_with_expiration(TOKEN_BLACKLIST_SET, refresh_token):
            raise ValueError("Invalid refresh token")
        
        payload = decode_token(refresh_token, get_token_secret())
        user_id = payload["id"]
        user = await self.user_service.get_user("id", user_id)
        
        if not user:
            raise ValueError("Invalid user")
        
        expires_at = int(payload["exp"])
        remaining_seconds = expires_at - int(time())
        
        add_to_set_with_expiration(
            key=TOKEN_BLACKLIST_SET, 
            value=refresh_token, 
            expiration=remaining_seconds
        )
        
        return self._generate_tokens(str(user.id))
    
    async def complete_oauth_code_flow(
        self,
        provider: OAuthProvider,
        code: str
    ) -> Tuple[str, str, int]:
        """
        Provided an OAuth provider and code, completes the OAuth flow to authenticate a user and generate tokens

        Args:
            code (str): The OAuth code provided by the provider
        """

        user: Optional[User] = None

        if provider == OAuthProvider.GITHUB:
            access_token = exchange_github_code_for_token(code)
            github_user = get_github_user_info(access_token)
            
            try:
                user = await self.user_service.get_user("email", github_user.email_address)
            except ValueError:
                user = await self.user_service.create_external_user(
                    provider=provider,
                    user_id=github_user.username,
                    email_address=github_user.email_address,
                    avatar_url=github_user.avatar_url
                )
        elif provider == OAuthProvider.GOOGLE:
            access_token = exchange_google_code_for_token(code)
            google_user = get_google_user_info(access_token)
            
            try:
                user = await self.user_service.get_user("email", google_user.email_address)
            except ValueError:
                user = await self.user_service.create_external_user(
                    provider=provider,
                    user_id=google_user.username,
                    email_address=google_user.email_address,
                    avatar_url=google_user.avatar_url
                )
    
        return self._generate_tokens(str(user.id))
    
    def _generate_tokens(
        self, 
        user_id: str
    ) -> Tuple[str, str, int]:
        """
        Generates a new user access token using configuration values for signing key and expiration

        Args:
            user_id (str): The user's unique identifier

        Returns:
            Tuple[str, str, int]: The generated access token, refresh token and expiration time
        """
        signing_key = get_token_secret()
        token_expiration_minutes = get_token_expiration_minutes()
        refresh_token_expiration_days = get_refresh_token_expiration_days()
        
        access_token = create_token({"id": user_id}, signing_key, token_expiration_minutes)
        refresh_token = create_token({"id": user_id}, signing_key, refresh_token_expiration_days * DAYS_TO_MINUTES)
    
        return access_token, refresh_token, token_expiration_minutes * MINUTES_TO_SECONDS
    
    def _verify_password(
        self, 
        plain: str, 
        hashed: str
    ) -> bool:
        """
        Verifies a provided password against the correct hash

        Args:
            plain (str): The plain text password
            hashed (str): The hashed password to compare against

        Returns:
            bool: Whether the password is correct
        """
        return self.crypto_context.verify(plain, hashed)
    
    def _get_password_hash(
        self, 
        password: str
    ) -> str:
        """
        Generates a cryptographic hash of a password using the configured hashing algorithm (bcrypt)

        Args:
            password (str): The plaintext password to hash

        Returns:
            str: A hashed version of the password
        """
        return self.crypto_context.hash(password)