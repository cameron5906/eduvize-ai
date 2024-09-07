from fastapi import APIRouter, Depends, Response
from config import get_dashboard_endpoint
from app.services import UserOnboardingService
from app.services.user_onboarding_service import VerificationExpiredError

router = APIRouter(
    prefix="/onboarding",
)

@router.get("/verify")
async def verify_user(
    code: str, 
    user_onboarding_service: UserOnboardingService = Depends(UserOnboardingService)
):
    try:
        await user_onboarding_service.verify_user(code)
        
        # If successful, redirect them to the dashboard
        dashboard_endpoint = get_dashboard_endpoint()
        return Response(status_code=307, headers={"location": dashboard_endpoint})
    except ValueError as e:
        return Response(status_code=400, content=str(e))
    except VerificationExpiredError as e:
        return Response(status_code=400, content="Verification code has expired")