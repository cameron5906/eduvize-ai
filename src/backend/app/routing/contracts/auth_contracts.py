from pydantic import BaseModel

class RegistrationPayload(BaseModel):
    username: str
    email: str
    password: str
    
class AuthenticationPayload(BaseModel):
    email: str
    password: str
    
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    
class TokenRefreshPayload(BaseModel):
    refresh_token: str