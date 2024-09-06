import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.services import AuthService
from app import app
from domain.enums.auth import OAuthProvider
from app.routing.contracts.auth_contracts import AuthenticationPayload, OAuthPayload, RegistrationPayload, RefreshTokenPayload

client = TestClient(app)

# Helper function to override dependency injection with the mock
def override_auth_service(mock_auth_service: AuthService):
    return mock_auth_service

@patch("app.services.AuthService", autospec=True)
@pytest.mark.asyncio
async def test_login(mock_auth_service: AuthService):
    """
    Tests that the login endpoint works as expected:
    1. Status code is 200
    2. Response contains access_token, refresh_token, and expires_in
    3. AuthService.authenticate is called with the correct arguments
    """
    
    # Mock the authenticate method
    mock_auth_service.authenticate = AsyncMock(return_value=("access_token", "refresh_token", 3600))

    # Override the AuthService dependency
    app.dependency_overrides[AuthService] = lambda: mock_auth_service

    payload = {
        "email": "test@example.com",
        "password": "testpassword"
    }
    response = client.post("/api/auth/login", json=payload)

    # Ensure the mock was called and response is correct
    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600
    }

    mock_auth_service.authenticate.assert_awaited_once_with("test@example.com", "testpassword")

    # Clear overrides after test
    app.dependency_overrides = {}

@patch("app.services.AuthService", autospec=True)
@pytest.mark.asyncio
async def test_register(mock_auth_service: AuthService):
    """
    Tests that the register endpoint works as expected:
    1. Status code is 200
    2. Response contains access_token, refresh_token, and expires_in
    3. AuthService.register is called with the correct arguments
    """

    mock_auth_service.register = AsyncMock(return_value=("access_token", "refresh_token", 3600))

    # Override the AuthService dependency
    app.dependency_overrides[AuthService] = lambda: mock_auth_service

    payload = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword"
    }
    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600
    }

    mock_auth_service.register.assert_awaited_once_with("test@example.com", "testuser", "testpassword")

    # Clear overrides after test
    app.dependency_overrides = {}

@patch("app.services.AuthService", autospec=True)
@pytest.mark.asyncio
async def test_oauth_login(mock_auth_service: AuthService):
    """
    Tests that the oauth_login endpoint works as expected:
    1. Status code is 200
    2. Response contains access_token, refresh_token, and expires_in
    3. AuthService.complete_oauth_code_flow is called with the correct arguments
    """
    
    mock_auth_service.complete_oauth_code_flow = AsyncMock(return_value=("access_token", "refresh_token", 3600))

    # Override the AuthService dependency
    app.dependency_overrides[AuthService] = lambda: mock_auth_service

    payload = {
        "code": "oauth_code"
    }
    provider = OAuthProvider.GOOGLE.value
    response = client.post(f"/api/auth/oauth/{provider}", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600
    }

    mock_auth_service.complete_oauth_code_flow.assert_awaited_once_with(OAuthProvider.GOOGLE, "oauth_code")

    # Clear overrides after test
    app.dependency_overrides = {}

@patch("app.services.AuthService", autospec=True)
@pytest.mark.asyncio
async def test_refresh_token(mock_auth_service: AuthService):
    """
    Tests that the refresh endpoint works as expected:
    1. Status code is 200
    2. Response contains access_token, refresh_token, and expires_in
    3. AuthService.refresh_access is called with the correct arguments
    """
    
    mock_auth_service.refresh_access = AsyncMock(return_value=("access_token", "refresh_token", 3600))

    # Override the AuthService dependency
    app.dependency_overrides[AuthService] = lambda: mock_auth_service

    payload = {
        "refresh_token": "old_refresh_token"
    }
    response = client.post("/api/auth/refresh", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access_token",
        "refresh_token": "refresh_token",
        "expires_in": 3600
    }

    mock_auth_service.refresh_access.assert_awaited_once_with("old_refresh_token")

    # Clear overrides after test
    app.dependency_overrides = {}

@patch("app.services.AuthService", autospec=True)
@pytest.mark.asyncio
async def test_logout(mock_auth_service: AuthService):
    """
    Tests that the logout endpoint works as expected:
    1. Status code is 200
    2. AuthService.logout is called with the correct arguments
    """
    
    mock_auth_service.logout = AsyncMock()

    # Override the AuthService dependency
    app.dependency_overrides[AuthService] = lambda: mock_auth_service

    payload = {
        "refresh_token": "refresh_token"
    }
    access_token = "access_token"
    response = client.request("DELETE", "/api/auth/", json=payload, headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200

    mock_auth_service.logout.assert_called_once_with(
        access_token="access_token",
        refresh_token="refresh_token"
    )

    # Clear overrides after test
    app.dependency_overrides = {}
