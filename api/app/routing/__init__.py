from fastapi import APIRouter

api_router = APIRouter()

from .onboarding_router import router as onboarding_router
from .user_router import router as user_router
from .auth_router import router as auth_router
from .autocomplete_router import router as autocomplete_router
from .file_router import router as file_router

api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(onboarding_router)
api_router.include_router(autocomplete_router)
api_router.include_router(file_router)