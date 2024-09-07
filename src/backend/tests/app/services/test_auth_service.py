import pytest
from unittest.mock import AsyncMock, patch, Mock
from time import time
from app.services.auth_service import AuthService
from domain.enums.auth import OAuthProvider
from domain.schema.user import User

@patch("app.services.auth_service.AuthService._generate_tokens", autospec=True)
@pytest.mark.asyncio
async def test_authenticate(mock_generate_tokens):
    """
    Tests the authenticate method:
    1. Retrieves the user from the user service
    2. Verifies the password
    3. Generates access and refresh tokens for the user
    """
    mock_user_service = Mock()
    mock_user_service.get_user = AsyncMock(return_value=User(id="user123", password_hash="hashed_password"))

    auth_service = AuthService(user_service=mock_user_service)

    # Mock password verification
    auth_service._verify_password = Mock(return_value=True)

    # Mock token generation
    mock_generate_tokens.return_value = ("access_token", "refresh_token", 3600)

    result = await auth_service.authenticate(email="test@example.com", password="password123")

    # Assertions
    mock_user_service.get_user.assert_awaited_once_with("email", "test@example.com")
    auth_service._verify_password.assert_called_once_with("password123", "hashed_password")
    mock_generate_tokens.assert_called_once_with(auth_service, "user123")
    assert result == ("access_token", "refresh_token", 3600)


@patch("app.services.auth_service.AuthService._generate_tokens", autospec=True)
@patch("app.services.auth_service.AuthService._get_password_hash", autospec=True)
@pytest.mark.asyncio
async def test_register(mock_get_password_hash, mock_generate_tokens):
    """
    Tests the register method:
    1. Hashes the password
    2. Creates a new user
    3. Generates access and refresh tokens for the user
    """
    mock_user_service = Mock()
    mock_user_service.create_user = AsyncMock(return_value=User(id="user123"))

    auth_service = AuthService(user_service=mock_user_service)

    # Mock password hashing
    mock_get_password_hash.return_value = "hashed_password"
    # Mock token generation
    mock_generate_tokens.return_value = ("access_token", "refresh_token", 3600)

    result = await auth_service.register(email="test@example.com", username="testuser", password="password123")

    # Assertions
    mock_get_password_hash.assert_called_once_with(auth_service, "password123")
    mock_user_service.create_user.assert_awaited_once_with("test@example.com", "testuser", "hashed_password")
    mock_generate_tokens.assert_called_once_with(auth_service, "user123")
    assert result == ("access_token", "refresh_token", 3600)


@patch("app.services.auth_service.get_token_secret", return_value="mock_secret")
@patch("app.services.auth_service.decode_token", autospec=True)
@patch("app.services.auth_service.add_to_set_with_expiration", autospec=True)
@pytest.mark.asyncio
async def test_logout(mock_add_to_set_with_expiration, mock_decode_token, mock_get_token_secret):
    """
    Tests the logout method:
    1. Calls decode_token to decode both access and refresh tokens
    2. Adds both tokens to the blacklist cache with correct expiration
    """
    mock_decode_token.side_effect = [
        {"exp": int(time()) + 3600, "id": "user123"},  # Access token
        {"exp": int(time()) + 7200, "id": "user123"},  # Refresh token
    ]

    auth_service = AuthService()

    auth_service.logout("access_token", "refresh_token")

    # Assertions
    mock_decode_token.assert_any_call("access_token", "mock_secret")
    mock_decode_token.assert_any_call("refresh_token", "mock_secret")

    mock_add_to_set_with_expiration.assert_any_call(
        key="stale_tokens", value="access_token", expiration=3600
    )
    mock_add_to_set_with_expiration.assert_any_call(
        key="stale_tokens", value="refresh_token", expiration=7200
    )


@patch("app.services.auth_service.get_token_secret", return_value="mock_secret")
@patch("app.services.auth_service.AuthService._generate_tokens", autospec=True)
@patch("app.services.auth_service.decode_token", autospec=True)
@patch("app.services.auth_service.add_to_set_with_expiration", autospec=True)
@patch("app.services.auth_service.is_in_set_with_expiration", autospec=True)
@pytest.mark.asyncio
async def test_refresh_access(mock_is_in_set_with_expiration, mock_add_to_set_with_expiration, mock_decode_token, mock_generate_tokens, mock_get_token_secret):
    """
    Tests the refresh_access method:
    1. Verifies that the refresh token is not in the blacklist
    2. Calls _generate_tokens to create new tokens
    3. Adds the refresh token to the blacklist with correct expiration
    """
    mock_is_in_set_with_expiration.return_value = False
    mock_decode_token.return_value = {"id": "user123", "exp": int(time()) + 3600}
    mock_generate_tokens.return_value = ("new_access_token", "new_refresh_token", 3600)

    mock_user_service = Mock()
    mock_user_service.get_user = AsyncMock(return_value=User(id="user123"))

    auth_service = AuthService(user_service=mock_user_service)

    result = await auth_service.refresh_access(refresh_token="valid_refresh_token")

    # Assertions
    mock_is_in_set_with_expiration.assert_called_once_with("stale_tokens", "valid_refresh_token")
    mock_decode_token.assert_called_once_with("valid_refresh_token", "mock_secret")
    mock_add_to_set_with_expiration.assert_called_once()
    mock_generate_tokens.assert_called_once_with(auth_service, "user123")
    assert result == ("new_access_token", "new_refresh_token", 3600)


@patch("app.services.auth_service.exchange_github_code_for_token", autospec=True)
@patch("app.services.auth_service.get_github_user_info", autospec=True)
@patch("app.services.auth_service.AuthService._generate_tokens", autospec=True)
@pytest.mark.asyncio
async def test_complete_oauth_code_flow_github(mock_generate_tokens, mock_get_github_user_info, mock_exchange_github_code_for_token):
    """
    Tests the complete_oauth_code_flow method for GitHub:
    1. Calls exchange_github_code_for_token to get the access token
    2. Calls get_github_user_info to get user details
    3. Generates access and refresh tokens for the user
    """
    mock_exchange_github_code_for_token.return_value = "github_access_token"
    mock_get_github_user_info.return_value = Mock(email_address="github_user@example.com", username="github_user", avatar_url="avatar_url")

    mock_user_service = Mock()
    mock_user_service.get_user = AsyncMock(side_effect=ValueError)  # User not found, create a new one
    mock_user_service.create_external_user = AsyncMock(return_value=User(id="user123"))

    mock_generate_tokens.return_value = ("access_token", "refresh_token", 3600)

    auth_service = AuthService(user_service=mock_user_service)

    result = await auth_service.complete_oauth_code_flow(provider=OAuthProvider.GITHUB, code="valid_code")

    # Assertions
    mock_exchange_github_code_for_token.assert_called_once_with("valid_code")
    mock_get_github_user_info.assert_called_once_with("github_access_token")
    mock_user_service.create_external_user.assert_awaited_once_with(
        provider=OAuthProvider.GITHUB,
        user_id="github_user",
        email_address="github_user@example.com",
        avatar_url="avatar_url"
    )
    mock_generate_tokens.assert_called_once_with(auth_service, "user123")
    assert result == ("access_token", "refresh_token", 3600)


def test_verify_password():
    """
    Tests the _verify_password method:
    1. Correctly verifies the password using the crypto_context
    """
    mock_crypto_context = Mock()
    mock_crypto_context.verify = Mock(return_value=True)

    auth_service = AuthService()
    auth_service.crypto_context = mock_crypto_context

    result = auth_service._verify_password("plain_password", "hashed_password")

    # Assertions
    mock_crypto_context.verify.assert_called_once_with("plain_password", "hashed_password")
    assert result is True


def test_get_password_hash():
    """
    Tests the _get_password_hash method:
    1. Hashes the password using the crypto_context
    """
    mock_crypto_context = Mock()
    mock_crypto_context.hash = Mock(return_value="hashed_password")

    auth_service = AuthService()
    auth_service.crypto_context = mock_crypto_context

    result = auth_service._get_password_hash("plain_password")

    # Assertions
    mock_crypto_context.hash.assert_called_once_with("plain_password")
    assert result == "hashed_password"
