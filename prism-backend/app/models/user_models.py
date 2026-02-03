from typing import Optional
from pydantic import BaseModel, EmailStr


class User(BaseModel):
    user_id: str
    email: EmailStr
    name: Optional[str] = None
    role: str = "user"  # "user" or "admin"
    timezone: Optional[str] = "Asia/Kolkata"
