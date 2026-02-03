from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime, timezone
from typing import Optional

router = APIRouter()

class FormSubmission(BaseModel):
    name: str
    email: EmailStr
    message: str

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str):
        v = v.strip()
        if not v:
            raise ValueError('Name is required')
        import re
        if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,100}$", v):
            raise ValueError("Use letters, spaces, apostrophes, hyphens")
        return v

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str):
        v = v.strip()
        if len(v) < 10:
            raise ValueError('Message must be at least 10 characters')
        if len(v) > 2000:
            raise ValueError('Message too long')
        return v

@router.post('/api/form')
async def submit_form(payload: FormSubmission):
    """Accept contact form submissions and persist to MongoDB if available."""
    doc = {
        'name': payload.name,
        'email': str(payload.email),
        'message': payload.message,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    try:
        from app.db.mongo_client import db
        await db.incoming_forms.insert_one(doc)
        return { 'status': 'ok', 'message': 'Saved' }
    except Exception:
        # Fallback: accept without DB (e.g., during local dev)
        return { 'status': 'ok', 'message': 'Accepted (not persisted)' }
