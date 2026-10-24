"""HTTP authentication inputs contain no provider-specific fields."""

from pydantic import BaseModel, Field

ACCESS_COOKIE = "medi_chat_access_token"
REFRESH_COOKIE = "medi_chat_refresh_token"


class LoginInput(BaseModel):
    login_id: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=15, max_length=128, repr=False)


class PrincipalResponse(BaseModel):
    user_id: str
    expires_at: int


class LoginResponse(PrincipalResponse):
    refresh_expires_at: int
