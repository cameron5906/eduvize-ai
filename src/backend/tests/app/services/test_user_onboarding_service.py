import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import datetime
from app.services.user_onboarding_service import UserOnboardingService, VerificationExpiredError
from domain.dto.user import UserOnboardingStatusDto, UserProfileDto
from domain.dto.profile import UserProfileDisciplineDto, UserSkillDto, UserSkillType, UserDiscipline
from domain.dto.profile.hobby import UserProfileHobbyDto, HobbyReason

# Sample data
user_id = "user123"
verification_code = "random_code"
email = "test@example.com"
current_time = datetime.datetime.utcnow()

profile_dto = UserProfileDto(
    first_name="John",
    last_name="Doe",
    bio="Sample bio",
    disciplines=[
        UserProfileDisciplineDto(
            discipline_type=UserDiscipline.BACKEND,
        )             
    ],
    skills=[
        UserSkillDto(
            skill_type=UserSkillType.PROGRAMMING_LANGUAGE,
            skill="Python",
        )        
    ],
    hobby=UserProfileHobbyDto(
        reasons=[HobbyReason.CHALLENGING],
        projects=[]
    )
)

user_mock = MagicMock(
    id=user_id,
    username="john_doe",
    email=email,
    verification_code=verification_code,
    pending_verification=False,
    profile=profile_dto,
    verification_sent_at_utc=current_time,
)

@pytest.fixture
def user_onboarding_service():
    user_repo = MagicMock()
    return UserOnboardingService(user_repository=user_repo)

### Test send_verification_email ###
@pytest.mark.asyncio
@patch("app.services.user_onboarding_service.generate_random_string", autospec=True)
@patch("app.services.user_onboarding_service.get_verification_url", autospec=True)
@patch("app.services.user_onboarding_service.get_welcome_email", autospec=True)
@patch("app.services.user_onboarding_service.send_email", autospec=True)
async def test_send_verification_email(
    mock_send_email, 
    mock_get_welcome_email, 
    mock_get_verification_url, 
    mock_generate_random_string, 
    user_onboarding_service
):
    """
    Tests the send_verification_email method:
    1. Should generate a verification code.
    2. Should send an email with the correct body.
    3. Should reset the verification code in the database.
    """
    # Mock repository to return user
    user_onboarding_service.user_repo.get_user = AsyncMock(return_value=user_mock)
    user_onboarding_service.user_repo.set_verification_code = AsyncMock()  # Use AsyncMock here
    
    # Mock the random string generation and email components
    mock_generate_random_string.return_value = verification_code
    mock_get_verification_url.return_value = "http://test.com/verify?code=random_code"
    mock_get_welcome_email.return_value = "Welcome Email Body"
    
    await user_onboarding_service.send_verification_email(user_id=user_id)
    
    # Assertions
    user_onboarding_service.user_repo.get_user.assert_awaited_once_with("id", user_id)
    mock_generate_random_string.assert_called_once_with(12)
    mock_get_verification_url.assert_called_once_with(verification_code)
    mock_get_welcome_email.assert_called_once_with(
        username=user_mock.username,
        verification_link="http://test.com/verify?code=random_code"
    )
    mock_send_email.assert_called_once_with(user_mock.email, "Wecome to Eduvize", "Welcome Email Body")
    user_onboarding_service.user_repo.set_verification_code.assert_awaited_once_with(user_id, verification_code)

### Test verify_user ###
@pytest.mark.asyncio
async def test_verify_user_success(user_onboarding_service):
    """
    Tests verify_user method for a valid verification code:
    1. Should verify the user successfully.
    """
    # Mock repository and current time
    user_onboarding_service.user_repo.get_user = AsyncMock(return_value=user_mock)
    user_onboarding_service.user_repo.mark_verified = AsyncMock()  # Ensure mark_verified is AsyncMock
    
    await user_onboarding_service.verify_user(code=verification_code)
    
    # Assertions
    user_onboarding_service.user_repo.get_user.assert_awaited_once_with("verification_code", verification_code)
    user_onboarding_service.user_repo.mark_verified.assert_awaited_once_with(user_mock.id)

@pytest.mark.asyncio
async def test_verify_user_expired_code(user_onboarding_service):
    """
    Tests verify_user method for an expired verification code:
    1. Should raise VerificationExpiredError.
    """
    # Mock an expired code by setting the sent time to 2 hours ago
    expired_time = current_time - datetime.timedelta(hours=2)
    expired_user_mock = MagicMock(**user_mock.__dict__)
    expired_user_mock.verification_sent_at_utc = expired_time
    
    # Mock repository
    user_onboarding_service.user_repo.get_user = AsyncMock(return_value=expired_user_mock)
    user_onboarding_service.user_repo.mark_verified = AsyncMock()
    
    with pytest.raises(VerificationExpiredError):
        await user_onboarding_service.verify_user(code=verification_code)

    # Assertions
    user_onboarding_service.user_repo.get_user.assert_awaited_once_with("verification_code", verification_code)
    user_onboarding_service.user_repo.mark_verified.assert_not_awaited()

### Test get_onboarding_status ###
@pytest.mark.asyncio
async def test_get_onboarding_status(user_onboarding_service):
    """
    Tests get_onboarding_status method:
    1. Should return correct onboarding status.
    """
    # Mock repository
    user_onboarding_service.user_repo.get_user = AsyncMock(return_value=user_mock)
    user_onboarding_service.is_profile_complete = AsyncMock(return_value=True)
    
    result = await user_onboarding_service.get_onboarding_status(user_id=user_id)
    
    # Assertions
    user_onboarding_service.user_repo.get_user.assert_awaited_once_with("id", user_id, ["profile"])
    user_onboarding_service.is_profile_complete.assert_awaited_once_with(user_id)
    
    assert isinstance(result, UserOnboardingStatusDto)
    assert result.is_verified == (not user_mock.pending_verification)
    assert result.is_profile_complete is True

### Test is_profile_complete ###
@pytest.mark.asyncio
async def test_is_profile_complete(user_onboarding_service):
    """
    Tests is_profile_complete method:
    1. Should return True for a complete profile.
    2. Should return False for an incomplete profile.
    """
    # Mock repository with a complete profile
    user_onboarding_service.user_repo.get_user = AsyncMock(return_value=user_mock)
    
    result = await user_onboarding_service.is_profile_complete(user_id=user_id)
    
    user_onboarding_service.user_repo.get_user.assert_awaited_once_with(
        by="id", value=user_id, include=["profile.*"]
    )
    
    assert result is True

    # Test for an incomplete profile
    incomplete_profile_user = MagicMock(**user_mock.__dict__)
    incomplete_profile_user.profile = UserProfileDto(first_name="John")
    user_onboarding_service.user_repo.get_user = AsyncMock(return_value=incomplete_profile_user)
    
    result = await user_onboarding_service.is_profile_complete(user_id=user_id)
    
    assert result is False
