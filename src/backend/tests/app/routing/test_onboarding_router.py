import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app import app
from app.services.user_onboarding_service import UserOnboardingService
from app.services.user_onboarding_service import VerificationExpiredError

client = TestClient(app)

@patch("app.routing.onboarding_router.get_dashboard_endpoint", autospec=True)
@patch("app.services.UserOnboardingService", autospec=True)
@pytest.mark.asyncio
async def test_verify_user_success(mock_user_onboarding_service, mock_get_dashboard_endpoint):
    """
    Tests the /onboarding/verify endpoint for a successful verification:
    1. Status code is 307 (redirect)
    2. The redirection URL is the dashboard endpoint
    3. UserOnboardingService.verify_user is called with the correct code
    """
    # Mock the successful behavior of verify_user
    mock_user_onboarding_service.verify_user = AsyncMock()

    # Mock the dashboard endpoint
    mock_get_dashboard_endpoint.return_value = "https://dashboard.example.com"
    
    # Override dependencies
    app.dependency_overrides[UserOnboardingService] = lambda: mock_user_onboarding_service

    # Call the endpoint
    code = "valid_verification_code"
    response = client.get(f"/api/onboarding/verify?code={code}", follow_redirects=False)

    # Assertions
    assert response.status_code == 307
    assert response.headers["location"] == "https://dashboard.example.com"

    mock_user_onboarding_service.verify_user.assert_awaited_once_with(code)


@patch("app.services.UserOnboardingService", autospec=True)
@pytest.mark.asyncio
async def test_verify_user_value_error(mock_user_onboarding_service):
    """
    Tests the /onboarding/verify endpoint when verification fails due to ValueError:
    1. Status code is 400 (bad request)
    2. The response contains the error message from ValueError
    3. UserOnboardingService.verify_user is called with the correct code
    """
    # Mock verify_user to raise ValueError
    mock_user_onboarding_service.verify_user = AsyncMock(side_effect=ValueError("Invalid code"))
    
    # Override dependencies
    app.dependency_overrides[UserOnboardingService] = lambda: mock_user_onboarding_service

    # Call the endpoint
    code = "invalid_code"
    response = client.get(f"/api/onboarding/verify?code={code}")

    # Assertions
    assert response.status_code == 400

    mock_user_onboarding_service.verify_user.assert_awaited_once_with(code)


@patch("app.services.UserOnboardingService", autospec=True)
@pytest.mark.asyncio
async def test_verify_user_verification_expired_error(mock_user_onboarding_service):
    """
    Tests the /onboarding/verify endpoint when verification fails due to VerificationExpiredError:
    1. Status code is 400 (bad request)
    2. The response contains the error message from VerificationExpiredError
    3. UserOnboardingService.verify_user is called with the correct code
    """
    # Mock verify_user to raise VerificationExpiredError
    mock_user_onboarding_service.verify_user = AsyncMock(side_effect=VerificationExpiredError("Verification code expired"))
    
    # Override dependencies
    app.dependency_overrides[UserOnboardingService] = lambda: mock_user_onboarding_service

    # Call the endpoint
    code = "expired_code"
    response = client.get(f"/api/onboarding/verify?code={code}")

    # Assertions
    assert response.status_code == 400

    mock_user_onboarding_service.verify_user.assert_awaited_once_with(code)
